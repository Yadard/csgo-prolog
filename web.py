from dataclasses import dataclass, field
from urllib.parse import unquote
import re
from typing import List
from bs4 import BeautifulSoup
import requests
from time import sleep

@dataclass
class Record:
    duration: str
    team: str

@dataclass
class TournamentResult:
    tournament: str
    team: str
    date: str
    prize: str

@dataclass
class Player:
    nick: str
    name: str
    nationality: List[str]
    birth: str
    activite: str
    role: str
    captain: str
    teams: List[str]
    history: List[Record] = field(default_factory=list)
    champion: List[TournamentResult] = field(default_factory=list)
    vice: List[TournamentResult] = field(default_factory=list)

def get_team() -> List[str]:
    links: List[str] = []
    result = requests.get(r"https://liquipedia.net/counterstrike/Portal:Teams")

    bs = BeautifulSoup(result.text, features='lxml')
    table = bs.find_all('table')[0]

    
    for team in table.find_all('li'):
        links.append(team.find_all('a')[1]['href'])


    return links

@dataclass
class PlayerLink:
    link: str
    captain: str

def get_players(teams: List[str]) -> List[PlayerLink]:
    pls:List[PlayerLink] = []
    for team in teams[50:120]:
        sleep(0.250)
        result = requests.get(f"https://liquipedia.net{team}")
        print(team, result)
        bs = BeautifulSoup(result.text, features='lxml')

        table = bs.find_all('div', class_='table-responsive')[0]
        players = table.find_all('tr', class_='Player')
        for p in players:
            anchors = p.find_all('a')
            player = PlayerLink(anchors[0]['href'], unquote(team.replace("/counterstrike/",'')).replace('_', ' ') if p.find('a', title="Captain") else '')
            if 'index.php' in player.link:
                continue
            print('\t', player)
            pls.append(player)

    return pls

def get_player_info(player: PlayerLink) -> Player | None:
    print(f"https://liquipedia.net{player.link}")
    result = requests.get(f"https://liquipedia.net{player.link}")
    print(result)

    nick_re = r'\w+$'
    bs = BeautifulSoup(result.text, features='lxml')
    root =  bs.find_all('div', class_='infobox-cs2')
    if root == []:
        root = bs.find_all('div', class_='infobox-cs')
    if root == []:
        root = bs.find_all('div', class_='infobox-csgo')
    if root == []:
        return None
    card = root[0].find_all('div', recursive=False)[0]
    info = card.find_all('div', recursive=False)
    print("nick", info[0].find('div').text)
    nick = re.search(nick_re, info[0].find('div').text)
    if nick:
        nick = nick.group(0)
    else:
        nick = "Error"
    info = info[3:]

    data = {}

    for div in info:
        divs = div.find_all('div', recursive=False)
        if len(divs) < 2:
            continue
        data.update({divs[0].text: divs[1]})

    if 'Romanized Name:' in data:
        name = data['Romanized Name:'].text
    elif 'Name:' in data:
        name = data['Name:'].text
    else:
        return None
    __nati = data['Nationality:'].find_all('a')
    nati = [__nati[i].text for i in range(1,len(__nati), 2)]
    birth = ""
    if 'Born:' in data:
        birth = data['Born:'].text.replace('\\xa0', '')
    acti = None
    if 'Years Active (Player):' in data:
        acti = data['Years Active (Player):'].text[:4]
    elif 'Years Active (Coach):' in data:
        acti = data['Years Active (Coach):'].text[:4]
    __as = []
    if 'Role:' in data:
        __as = data['Role:'].find_all('a')
    elif 'Roles:' in data:
        __as = data['Roles:'].find_all('a')
    role = ""
    for a in __as:
        role += f"|{a.text}, "
    team = []
    if 'Team:' in data:
        team = [a.text for a in data['Team:'].find_all('a')]
    elif 'Teams:' in data:
        team = [a.text for a in data['Teams:'].find_all('a')]

        


    # name = info[0].find_all('div')[1].text
    # padding = 1
    # while True:
    #     try:
    #         nati = info[0 + padding].find_all('div')[1].find_all('a')[1].text
    #         break;
    #     except (IndexError, AttributeError):
    #         padding += 1
    # nati = info[0 + padding].find_all('div')[1].find_all('a')[1].text
    # birth = info[1 + padding].find_all('div')[1].text.replace('\\xa0', '')
    # acti = info[3 + padding].find_all('div')[1].text
    # __as = info[4 + padding].find_all('div')[1].find_all('a')
    # role = ""
    # for a in __as:
    #     role += f"|{a.text}, "
    # try:
    #     team = info[5 + padding].find_all('div')[1].find('a').text
    # except AttributeError:
    #     team = info[5 + padding - 1].find_all('div')[1].find('a').text



    print(nick, name, nati, birth, acti, role, player.captain, team, sep='\n\t', end='\n\n')
    if not nick or not name or not nati or not birth or not acti or not role or not team:
        return None
    p = Player(nick, name, nati, birth, acti, role, player.captain, team)
    hist = info[-1].find('div', class_='infobox-center').find_all('div', recursive=False)
    for i in range(0, len(hist), 2):
        reco = hist[i]
        time = reco.find('div', class_='th-mono').find('i').text
        team = reco.find_all('div', recursive=False)[1].find('a').text
        p.history.append(Record(time, team))

    table = bs.find('center')
    tb = table.find('tbody')
    for data in tb.find_all('tr'):
        d = data.find_all('td')
        try:
            date = d[0].text
            tourn = d[6].find('a').text.replace('\"', '\\\"')
            try:
                team = d[7].find('img')['alt']
            except TypeError:
                team = "Unkown"
            prize = d[-1].text
            place = d[1].find('b').text[0]
            if place == '2':
                p.vice.append(TournamentResult(tourn, team, date, prize))
            elif place == '1':
                p.champion.append(TournamentResult(tourn, team, date, prize))
        except IndexError:
            pass
    return p



def dump_players(players: List[Player]) -> None:
    with open('prolog.txt', 'w',  encoding="utf-8") as db:
        db.write(
""":- discontiguous
        nick/2,
        age/2,
    	role/2,
        birth_month/2,
        birth_year/2,
		birth_day/2,
		nationality/2,
        entry_year/2,
        current_team/2,
        former_team/2,
        captain/2,
        champion/3,
        vice/3.

""")
        with open('rules.txt', 'r', encoding='utf-8') as rules:
            db.write(rules.read())

        for player in players:
            print("writting player: ", player.name)
            db.write(f"""nick("{player.name}", "{player.nick}").
entry_year("{player.name}", {player.activite[:4]}).
                     """)
            if player.birth:
                parse_birth = re.search(r'(\w*)\s+(\d*),\s+(\d*)\s+\(.*?(\d*)\)', player.birth)
                if parse_birth == None:
                    return

                month = parse_birth.group(1)
                day = int(parse_birth.group(2))
                year = int(parse_birth.group(3))
                age =int(parse_birth.group(4))
                
                db.write(f"""
age("{player.name}", {age}).
birth_month("{player.name}", "{month}").
birth_year("{player.name}", {year}).
birth_day("{player.name}", {day}).
""")

            if player.captain:
                db.write(f"captain(\"{player.name}\", \"{player.captain}\").\n")
            db.writelines([f"current_team(\"{player.name}\", \"{team}\").\n" for team in player.teams])
            db.writelines([f"nationality(\"{player.name}\", \"{nat}\").\n" for nat in player.nationality])

            db.writelines([f"former_team(\"{player.name}\", \"{team.team}\").\n" for team in player.history])

            re_role = re.finditer(r'\|(.*?),', player.role)
            roles = [f"role(\"{player.name}\", \"{role.group(1)}\").\n" for role in re_role]
            db.writelines(roles)
            db.writelines([f"champion(\"{player.name}\", \"{tour.tournament}\", \"{tour.team}\").\n" for tour in player.champion])
            db.writelines([f"vice(\"{player.name}\", \"{tour.tournament}\", \"{tour.team}\").\n" for tour in player.vice])
            db.write('\n\n')



def main() -> None:
    foo = get_team()
    print(foo[0], len(foo))
    links = get_players(foo)


    print(len(links))
    players: List[Player] = []
    for i in range(len(links)):
        sleep(0.200)
        p = get_player_info(links[i])
        if p:
            players.append(p)

    dump_players(players)


if __name__ == '__main__':
    main()
