from itertools import chain
from pathlib import Path
from time import sleep
from datetime import datetime

import requests
import lxml.html as lh
from tqdm import tqdm

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs

import csv

year = '2020'
month = '02'
day = 1

monthly_game_ids = []
monthly_pbp_data = {

}

while day <= 31:
    daily_game_ids = []
    day_source = requests.get(f'https://www.basketball-reference.com/boxscores/?month={month}&day={day}&year={year}')
    day_soup = bs(day_source.text, 'lxml')
    paras = day_soup.find_all('p', {'class':'links'})
    for p in paras:
        links = p.find_all('a')
        for link in links:
            if link.text == 'Play-By-Play':
                game_link = link['href'].split('/')
                game_id = game_link[3].split('.')[0]
                daily_game_ids.append(game_id)
    if daily_game_ids is not [] and daily_game_ids is not '':
        for game in daily_game_ids:    
            monthly_game_ids.append(game)
    day += 1

for game in monthly_game_ids:
    game_id = game
    pbp_source = requests.get(f'https://www.basketball-reference.com/boxscores/pbp/{game_id}.html')
    pbp_soup = bs(pbp_source.text, 'lxml')



    # ------------------------------------------------------------------------------
    # TEAM IDS----------------------------------------------------------------------
    # ------------------------------------------------------------------------------

    # Teams array
    teams = []

    # Pulls team divs
    scorebox = pbp_soup.find('div', {'class':'scorebox'})
    team_ids = scorebox.find_all('div', {'class':''})

    for div in team_ids:

        # Pulls link if div has link
        if div.find('a'):
            links = div.find_all('a')
            
            # Finds ids in link and appends to teams array
            for link in links:
                team_ids = link['href'].split('/')
                if len(team_ids[2]) == 3:
                    teams.append(team_ids)

    # Assigns team ids to correct teams
    home_team = teams[2][2]
    away_team = teams[0][2]

    # ------------------------------------------------------------------------------
    # PLAY BY PLAY DATA-------------------------------------------------------------
    # ------------------------------------------------------------------------------

    # Play by play variables
    game_data = []
    first_quarter = []
    second_quarter = []
    third_quarter = []
    fourth_quarter = []
    overtime = []

    # Pulls play by play table data
    table = pbp_soup.find_all('table')[0]
    rows = table.find_all('tr')

    for row in rows:

    # ADDING DATA ------------------------------------------------------------------
        # setup array for each play, player_id
        play_data = []

        # separates each td in the tr
        data = row.find_all('td')

        # scans for player_id using href
        if row.find('a'):
            id_array = []
            ids = row.find_all('a')
            for id in ids: 
                id_link = id['href'].split('/')
                if len(id_link) > 3:
                    id_array.append(id_link[3].split('.')[0])
            if len(id_array) > 1:
                player_id = id_array[0]
                second_id = id_array[1]
            else:
                if len(id_array) >= 1:
                    player_id = id_array[0]
                    second_id = ''
        else:
            player_id =  ''
            second_id = ''

        # iterates through data to pull text from each td
        for d in data:
            play_data.append(d.text)

        # adds player_id to end of array
        play_data.append(player_id)

    # REMOVING COMPLETELY USELESS DATA ---------------------------------------------

        # removes points scored
        if len(play_data) > 4:
            play_data.pop(4)
            play_data.pop(2)

        # removes other team data
        if len(play_data) > 3:
            # appends 2 for away, removes home team description
            if play_data[1] == '\xa0':
                play_data.append(2)
                play_data.pop(1)
            # appends 1 for home, removes away team description
            elif play_data[3] == '\xa0':
                play_data.append(1)
                play_data.pop(3)
                play_data[1], play_data[2] = play_data[2], play_data[1]

    # CLEANING DATA -----------------------------------------------------------------
        # Divides description into specific variable data
        if len(play_data) > 4:
            detail = play_data[2].split(' ')
            steal_detail = ''

            # Rebounds / rebound, rebound_type, null, null, null
            if detail[1] == 'rebound':
                play_data.append('rebound')
                # Returns Offensive/Defensive
                play_data.append(detail[0])
                play_data.append('')
                play_data.append('')
                play_data.append('')

            # Steals / steal, steal_type, null, stolen_from, null
            elif detail[0] == 'Turnover':

                # Filters non-steal turnovers
                if len(detail) > 6:
                    play_data.append(detail[6])
                    if detail[4] == '(lost':
                        play_data.append('lost')
                    elif detail[4] == '(bad':
                        play_data.append('pass')
                    play_data.append('')
                    play_data.append(player_id)
                    play_data.append('')
                    play_data[3] = second_id

            # Made Shots / make, shot_type, distance, assist_by, null
            elif detail[2] == 'makes':
                play_data.append('make')

                # 3-Pt Shots / shot_type, distance, assist_by, null
                if detail[3] == '3-pt':
                    play_data.append('3-pt')
                    play_data.append(detail[7])
                    play_data.append(second_id)
                    play_data.append('')

                # 2-Pt Shots / shot_type, distance, assist_by, null
                elif detail[3] == '2-pt':
                    play_data.append(detail[4])
                    
                    # Adjusts distance based on type (Dunk/Layups are at [6] while other shots are at [7])
                    if detail[4] == 'dunk' or detail[4] == 'layup':
                        play_data.append(detail[6])
                    else:
                        play_data.append(detail[7])
                    
                    play_data.append(second_id)
                    play_data.append('')

                # Free Throws / free, null, null, null, null
                elif detail[3] == 'free':
                    play_data.append('free')
                    play_data.append('')
                    play_data.append('')
                    play_data.append('')
                    play_data.append('')

            # Missed Shots / miss, shot_type, distance, null, block_by
            elif detail[2] == 'misses':

                # miss
                play_data.append('miss')

                # 3-Pt Shots / shot_type, distance, null, block_by
                if detail[3] == '3-pt':
                    play_data.append('3-pt')
                    play_data.append(detail[7])
                    play_data.append('')
                    play_data.append(second_id)

                # 2-Pt Shots / shot_type, distance, null, block_by
                elif detail[3] == '2-pt':
                    play_data.append(detail[4])

                    # Adjusts distance based on type (Dunk/Layups are at [6] while other shots are at [7])
                    if detail[4] == 'dunk' or detail[4] == 'layup':
                        play_data.append(detail[6])
                    else:
                        play_data.append(detail[7])
                    
                    play_data.append('')
                    play_data.append(second_id)

                # Free Throws / free, null, null, null, null
                elif detail[3] == 'free':
                    play_data.append('free')
                    play_data.append('')
                    play_data.append('')
                    play_data.append('')
                    play_data.append('')

            # Replace 'X-Y' Score Format with Differential Integer to make searching faster/calculate winning team
            score = play_data[1].split('-')
            score_difference = int(score[0]) - int(score[1])
            play_data[1] = score_difference

            # Removes description
            play_data.pop(2)


        # APPENDING DATA ---------------------------------------------------------------
        
        # Removes blanks
        if play_data[0] is not '':

            # Removes misc. items (substitutions, challenges, etc)
            if play_data[2] == '':
                # Keeps Quarter Divisions
                if type(play_data[1]) == str:
                    if play_data[1].split(' ')[3] == 'quarter':
                        game_data.append(play_data[1].split(' ')[2])
                    else:
                        game_data.append(play_data[1].split(' ')[3])
            # Removes team rebounds
            else:
                if len(play_data) > 5:
                    game_data.append(play_data)

    # ---------------------------------------------------------------------------------
    # POSTING DATA TO GAME DICTIONARY--------------------------------------------------
    # ---------------------------------------------------------------------------------

    # 1Q Indices
    first_quarter_min = 0
    first_quarter_max = game_data.index('2nd') - 2

    # 2Q Indices
    second_quarter_min = game_data.index('2nd') + 1
    second_quarter_max = game_data.index('3rd') - 2

    # 3Q Indices
    third_quarter_min = game_data.index('3rd') + 1
    third_quarter_max = game_data.index('4th') - 2

    # 4Q/OT Indices
    fourth_quarter_min = game_data.index('4th') + 1
    if 'overtime' in game_data:
        fourth_quarter_max = game_data.index('overtime') - 2
        overtime_min = game_data.index('overtime') + 1
        overtime_max = -1
    else:
        fourth_quarter_max = -1

    # Sets values to quarter variables
    first_quarter = game_data[first_quarter_min:first_quarter_max]
    second_quarter = game_data[second_quarter_min:second_quarter_max]
    third_quarter = game_data[third_quarter_min:third_quarter_max]
    fourth_quarter = game_data[fourth_quarter_min:fourth_quarter_max]
    if 'overtime' in game_data:
        overtime = game_data[overtime_min:overtime_max]

    # Sets up dictionary with key:value pairs for each game
    daily_pbp_data = {
        'game_id': game_id,
        'home': home_team,
        'away': away_team,
        'pbp': {
            '1q': first_quarter,
            '2q': second_quarter,
            '3q': third_quarter,
            '4q': fourth_quarter,
            'ot': overtime
        }
    }

    monthly_pbp_data[game_id] = daily_pbp_data



with open(f'{month}-pbp-data.csv', 'w') as csv_file:
    fieldnames = ['game_id', 'away_team', 'quarter', 'time', 'score_differential', 'player_id', 'home_or_away', 'play', 'play_type', 'distance', 'assist_by', 'block_by']
    dictwriter = csv.DictWriter(csv_file, fieldnames=fieldnames)
    dictwriter.writeheader()
    csvwriter = csv.writer(csv_file)
    for game in monthly_pbp_data:
        for quarter in monthly_pbp_data[game]['pbp']:
            for play in monthly_pbp_data[game]['pbp'][quarter]:
                csvwriter.writerow([game, monthly_pbp_data[game]['away'], quarter, *play])



# # for game in monthly_pbp_data:
# #     print(monthly_pbp_data[game]['home'])
# for game in monthly_pbp_data:
#     for quarter in monthly_pbp_data[game]['pbp']:
#         for play in monthly_pbp_data[game]['pbp'][quarter]:
#             print(game, quarter, *play, sep=', ')