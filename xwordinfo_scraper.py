import os
import requests
import time
import random
from bs4 import BeautifulSoup
from pprint import pprint
from datetime import date, timedelta

def get_clue_numbers(grid):
	# grid expected to be a list of strings like 'XXXXX.XXXX.XXXX'
	# where . indicates a black square
	down = []
	across = []
	number = 1
	increment_number = False
	for y in range(len(grid)):
		for x in range(len(grid[0])):  # assumes it's a rectangle, not necessarily square
			if grid[y][x] != '.':
				if (x == 0 and grid[y][1] != '.') or (grid[y][x-1] == '.' and not (x == len(grid[0])-1 or grid[y][x+1] == '.')):
					# makes sure it's not a one-letter gap, since those don't get clued
					across.append(number)
					increment_number = True
				if (y == 0 and grid[1][x] != '.') or (grid[y-1][x] == '.' and not (y == len(grid)-1 or grid[y+1][x] == '.')):
					down.append(number)
					increment_number = True
			if increment_number:
				number += 1
				increment_number = False
	return {'across': across, 'down': down}

def scrape_and_puz(start_date=date(1942, 2, 15), end_date=date(1993, 11, 20), overwrite=[False, False], puz_only = True):
    offset = 1
    daily_date = date(1950, 9, 10) # date NYT switched from weekly Sunday puzzles to daily puzzles
    if start_date < daily_date:
        offset = 6-start_date.weekday()
        working_date = start_date + timedelta(days=offset)
        if working_date != daily_date:
            offset = 7
    else:
        working_date = start_date
    
    h_path = 'nyt-cw/'
    p_path = 'nyt-puz/'
    fail_list = []
    if not puz_only and not os.path.exists(h_path):
        os.mkdir(h_path)
    if not os.path.exists(p_path):
        os.mkdir(p_path)
    h_path += working_date.strftime('%Y/')
    p_path += working_date.strftime('%Y/')
    if not puz_only and not os.path.exists(h_path):
        os.mkdir(h_path)
    if not os.path.exists(p_path):
        os.mkdir(p_path)
    h_path += working_date.strftime('%m/')
    p_path += working_date.strftime('%m/')
    if not puz_only and not os.path.exists(h_path):
        os.mkdir(h_path)
    if not os.path.exists(p_path):
        os.mkdir(p_path)

    while working_date <= end_date:
        if working_date == daily_date:
            offset = 1
        y, m, d = working_date.year, working_date.month, working_date.day
        if working_date <= daily_date or ((m, d) == (1, 1) and working_date != start_date):
            h_path = h_path[:-8]
            h_path += f'{y}/'
            p_path = p_path[:-8]
            p_path += f'{y}/'
            if not puz_only and not os.path.exists(h_path):
                os.mkdir(h_path)
            if not os.path.exists(p_path):
                os.mkdir(p_path)
            h_path += f'{m:0>2}/'
            p_path += f'{m:0>2}/'
            if not puz_only and not os.path.exists(h_path):
                os.mkdir(h_path)
            if not os.path.exists(p_path):
                os.mkdir(p_path)
        elif d == 1:
            h_path = h_path[:-3]
            p_path = p_path[:-3]
            h_path += f'{m:0>2}/'
            p_path += f'{m:0>2}/'
            if not puz_only and not os.path.exists(h_path):
                os.mkdir(h_path)    
            if not os.path.exists(p_path):
                os.mkdir(p_path)    

        filename = h_path + working_date.strftime('%b%d%y.html')
        p_name = p_path + working_date.strftime('%b%d%y.puz')
        if os.path.exists(filename) and not overwrite[0]:
            with open(filename, 'r') as f:
                text = f.read()
            if not os.path.exists(p_name) or overwrite[1]:
                try:
                    build_puz(parse(filename, text), p_name)
                except (ValueError, AttributeError, IndexError):
                    print(f'{filename} did not work')
            working_date += timedelta(days=offset)
            continue
        URL = f'https://www.xwordinfo.com/PS?date={m}/{d}/{y}'
        start = time.time()
        page = requests.get(URL)
        delay = time.time() - start
        time.sleep(random.uniform(2, 5) * delay)

        if 'not yet available' in page.text:
            return        
        if 'No valid puzzle' in page.text  \
           or 'are not available' in page.text \
           or 'Log in to your XWord Info account' in page.text \
           or ("Sunday, February 15, 1942" in page.text and (m, d, y) != (2, 15, 1942)): # don't know why it's pulling in the  first ever puzzle sometimes, but it is
            print(f'{filename} DNE')
            working_date += timedelta(days=offset)
            continue
        if not puz_only:
            with open(filename, 'w') as file:
                file.write(page.text)
        try:
            build_puz(parse(filename, page.text), p_name)
        except (ValueError, AttributeError, IndexError):
            print(filename)
            fail_list.append(filename)
        working_date += timedelta(days=offset)
    return fail_list


def checksum(start_bit, length, initial, array):
    cksum = initial
    for i in range(length):
        if cksum & 1:
            cksum = (cksum>>1) + 0x8000
        else:
            cksum = cksum >> 1
        cksum += array[start_bit + i]
    return cksum.to_bytes(2, 'little')

def parse(filename, full_text = None):
    if not full_text:
        with open(filename, 'r') as file:
            text = file.read()
    else:
        text = full_text
    replacements = {'\x95':'\xef', '\x87':'‡', '&#x1F497;':'[heart]', '&hearts;':'[heart]', '\u2764':'[heart]', '\u2665':'[heart]', '\ufe0f':'',
                    '&diams;':'[diamond]', '\u2666':'[diamond]', '&spades;':'[spade]', '\u2660':'[spade]', '&clubs;':'[club]', '\u2663':'[club]',
                    '\x82':'\xe2', '\x92':'?', '':'/', '':'\xe9', '&pi;':'[pi]', 'π':'[pi]', '&#9794;':'[male]', '&#9792;':'[female]',
                    '&Omega;':'[omega]', '&Sigma;':'[sigma]', '\u010d':'c', '\u02bb':"'", '∨':'||', '∧':'&', '¬':'~', '&sim;':'~', 'Đ':'D', 'ặ':'a',
                    'ắ':'a', '→':'->', 'ř':'r', '&#128308;':'[red dot]', '&#128993;':'[yellow dot]', '&#128994;':'[green dot]', '&#128309;':'[blue dot]',
                    '&#9899;':'[black dot]', '\u2639':':(', '&#x1F602;':'[crying laughing emoji]', '\U0001f602':'[crying laughing emoji]',
                    '\u03a3':'[sigma]', '&rarr;':'->', '&larr;':'<-', '&flat;':'b', '&#x1f913;':'[smiley face with glasses]', '&cup;':'[union]',
                    '&cap;':'[intersection]', '&#10004;':'[check]', '&check;':'[check]', '&#x2713;':'[check]', '&uarr;':'^', '&darr;':'v',
                    '&Theta;':'[Theta]', '&radic;':'[radical]', '\u03c1':'p', '&#x261c;':'[left pointing hand]', '&#x261e;':'[right pointing hand]',
                    '&#601;':'[upside-down e]'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    soup = BeautifulSoup(text, "html.parser")

    components = {'filename': filename[:filename.rfind('.')]}

    squares = soup.find(id="PuzTable").find_all("td")
    components['width'] = len(soup.find(id="PuzTable").find("tr").find_all("td"))
    components['length'] = len(squares)//components['width']
    grid = []
    rebuses = {}
    circled = set()
    for i in range(len(squares)):
        square = squares[i]
        if i % components['width'] == 0:
            if i != 0:
                grid.append(row)
            row = ''
        cl = square.get("class") or 'None'
        if cl[0] == "black" or cl[0] == "shape":
            row += '.'
        else:
            if cl != 'None' and cl[0] in ["shade", "bigcircle"]:
                circled.add(i) # used in the 'GEXT' section
            if cl[0] == "plot":
                continue
            try:
                text = square.find(class_="letter").text
            except AttributeError:
                #print(square)
                text = square.text[len(square.find(class_="num").text):]
                if text not in rebuses:
                    rebuses[text] = [i] # rebuses are combined if repeated, will deal with that in the 'GRBS' (grid rebus) and 'RTBL' (rebus table)
                else:
                    rebuses[text].append(i)
            try:
                row += text[0]
            except IndexError:
                try:
                    text = square['style']
                    text = text[text.rfind(':')+1:-1]
                    if text not in rebuses:
                        rebuses[text] = [i]
                    else:
                        rebuses[text].append(i)
                    row += text[0]

                except:
                    raise ValueError("empty cell")
    grid.append(row)

    components['grid'] = grid
    components['rebuses'] = rebuses
    components['circled'] = circled
    components['copyright'] = soup.find(id="CPHContent_Copyright").text
    # components['notes'] = soup.find(id="CPHContent_NotesPan").text.strip() # TODO: maybe dynamically check whether they reference a PDF/alt PUZ
    # this broader version ^ kept too much, often including spoilers. TODO: look into a better way to save these editor notes?
    try:
        notes = soup.find(class_="notepad").text.strip()
        if notes.startswith('Notepad: '):
            notes = notes[len('Notepad: '):]
    except AttributeError:
        notes = ''
    components['notes'] = notes
        
    try:
        author = soup.find(id="CPHContent_AEGrid").text.strip()
    except AttributeError:
        try:
            author = soup.find(class_="aegrid").text.strip()
        except:
            author = 'Author: Unknown'
    author = author[len('Author:'):]
    author = author.replace('\nEditor:', ' / ')
    components['author'] = author
    try:
        title = soup.find(id="CPHContent_SubTitle").text + ' ' + soup.find(id="PuzTitle").text # TODO: make sure this doesn't break when there isn't a title, just a date
    except AttributeError:
        title = soup.find(id="PuzTitle").text
    components['title'] = title.replace("New York", "NY")
    
    clues = {'across':{}, 'down': {}}
    uniclue = False
    clue_nums = get_clue_numbers(grid)
    if soup.find(class_="clueshead").text == 'Clues':
        # means we have a "Uniclue" puzzle, so Clue 1 is for 1A and 1D (assuming they exist)
        # so we need to figure out which clues actually exist in our puzzle
        uniclue = True
    try:
        across = soup.find(id="ACluesPan").find(class_="numclue").find_all("div")
    except AttributeError:
        across = soup.find(id="CPHContent_ACluesPan").find(class_="numclue").find_all("div")
    across_check = []
    down_check = []
    i = 0
    while i < len(across):
        clue_num = int(across[i].text)
        if not uniclue or clue_num in clue_nums['across']:
            clue_text = across[i+1].text
            clue_text = clue_text[:clue_text.rfind(':')-1]
            clues['across'][clue_num] = clue_text
            across_check.append(clue_num)
        if uniclue and clue_num in clue_nums['down']:
            clue_text = across[i+1].text
            clue_text = clue_text[:clue_text.rfind(':')-1]
            clues['down'][clue_num] = clue_text
            down_check.append(clue_num)
        i += 2
    if not uniclue:
        try:
            down = soup.find(id="DCluesPan").find(class_="numclue").find_all("div")
        except AttributeError:
            down = soup.find(id="CPHContent_DCluesPan").find(class_="numclue").find_all("div")
        i = 0
        while i < len(down):
            clue_num = int(down[i].text) # not sure if I want str or int for this
            clue_text = down[i+1].text
            clue_text = clue_text[:clue_text.rfind(':')-1]
            clues['down'][clue_num] = clue_text
            down_check.append(clue_num)
            i += 2
    #check whether clues we read actually match the grid
    if len(across_check) != len(set(across_check)) or len(down_check) != len(set(down_check)):
        print(across_check, down_check)
        raise IndexError("Duplicate clues")
    across_check = set(across_check)
    down_check = set(down_check)
    if across_check != clues['across'].keys() or down_check != clues['down'].keys():
        print(across_check, down_check, clues)
        raise IndexError("Clues don't match grid")
    if across_check != set(clue_nums['across']) or down_check != set(clue_nums['down']):
        # If the grid has extra clues that it shouldn't, that should be dealt with by hand (very situational)
        extra = ', '.join([f'{x}A' for x in across_check if x not in clue_nums['across']] + [f'{x}D' for x in down_check if x not in clue_nums['down']])
        if extra:
            print(clues)
            print(clue_nums)
            pprint(grid)
            raise IndexError("Grid missing included clues")
        # If it's just missing clues, you can basically always ignore them (standard is to put a '-')
        else:
            for a in clue_nums['across']:
                if a not in clues['across']:
                    clues['across'][a] = '-'
            for d in clue_nums['down']:
                if d not in clues['down']:
                    clues['down'][d] = '-'
            print(f'{filename} was missing clues and was filled in automatically')
        

    components['clues'] = clues
    components['num_clues'] = len(components['clues']['across'])+len(components['clues']['down'])
    return components

def checksum(start_bit:int, length:int, initial, array:bytearray):
    cksum = initial
    
    for i in range(length):
        if cksum & 1:
            cksum = (cksum>>1) + 0x8000
        else:
            cksum = cksum >> 1
        cksum += array[start_bit + i]
        cksum = cksum & 0x0FFFF
    return cksum.to_bytes(2, 'little')

def build_puz(components, save_to=None, verbose=False):
    if not save_to:
        save_to = components['filename']+'.puz'
        save_to = save_to.replace('cw', 'puz')
        print(save_to)
    output = bytearray(2)
    output.extend([ord(c) for c in 'ACROSS&DOWN\0'])
    output.extend(bytearray(10)) # this and the previous empty space are reserved for checksums
    output.extend(bytearray('1.3\0', encoding='windows-1252'))
    output.extend(bytearray(16)) # hard-coded this later
    output.extend([components['width'], components['length']])
    output.extend(components['num_clues'].to_bytes(2, 'little'))
    output.extend(b'\x01\x00\x00\x00') # more magic numbers? plus more unused scramble

    partial_board = '' # to calculate c_part later

    for line in components['grid']:
        output.extend(bytes(line, encoding='windows-1252'))
    for line in components['grid']:
        output.extend([45 + (c=='.') for c in line]) # empty grid, 45 for white squares, 46 for black
    for string in [components['title'], components['author'], components['copyright']]:
        output.extend(bytes(string+'\0', encoding='windows-1252')) #.replace(b'\xc2\xa9', b'\xa9'))
        partial_board += (string+'\0')

    # clues
    
    across = components['clues']['across']
    down = components['clues']['down']

    for n in range(1, max(max(across), max(down))+1):
        if verbose:
            print(n)
        if n in across:
            output.extend(bytes(across[n]+'\0', encoding="windows-1252"))
            partial_board += across[n]
        if n in down:
            output.extend(bytes(down[n]+'\0', encoding="windows-1252"))
            partial_board += down[n]
    output.extend(bytes(components['notes']+'\0', encoding="windows-1252"))
    if components['notes'] != '':
        partial_board += (components['notes']+'\0')

    # GEXT (another empty grid for save data and circles)    
    size = components['width']*components['length']
    size_b = size.to_bytes(2, 'little')
    output.extend(bytes('GEXT', encoding="windows-1252") + size_b)
    checksum_index = len(output)
    output.extend(bytes(size+3)) # 2 checksum + grid + 1 null terminator
    for i in components['circled']:
        output[checksum_index+2+i] = 0x80
    output[checksum_index:checksum_index+2] = checksum(checksum_index+2, size, 0, output)
        

    if components['rebuses'] != {}:
        # GRBS ("grid rebus", tells the rebus table which squares each rebus goes in)
        output.extend(bytes('GRBS', encoding="windows-1252") + size_b)
        checksum_index = len(output)
        output.extend(bytes(size+3))
        rebuses = components['rebuses']
        rebus_table = sorted(list(rebuses.keys()), key=lambda x: min(rebuses[x])) 
        for i, r in enumerate(rebus_table):
            for j in rebuses[r]:
                output[checksum_index+2+j] = i+2 # one more than index, normally 1-indexed
        output[checksum_index:checksum_index+2] = checksum(checksum_index+2, size, 0, output)

        # RTBL ("rebus table", indexes each rebus square)
        output.extend(bytes('RTBL', encoding="windows-1252"))
        checksum_index = len(output)
        output.extend(bytes(4))
        for i, r in enumerate(rebus_table):
            output.extend(bytes(f"{' '*(i<10)}{i+1}:{r};", encoding="windows-1252"))
        RTBL_len = len(output)-(checksum_index+4)
        output.extend(b'\x00')
        output[checksum_index:checksum_index+2] = RTBL_len.to_bytes(2, 'little')
        output[checksum_index+2:checksum_index+4] = checksum(checksum_index+4, RTBL_len, 0, output)

    # various checksums
    c_cib = checksum(0x2C, 8, 0, output)
    c_soln = checksum(0x34, size, 0, output)
    c_gext = checksum(0x34+size, size, 0, output)
    partial_board = bytearray(partial_board, encoding='windows-1252')
    c_part = checksum(0, len(partial_board), 0, partial_board)

    output[0x0E:0x10] = c_cib
    
    output[0x10] = 0x49 ^ c_cib[0]
    output[0x11] = 0x43 ^ c_soln[0]
    output[0x12] = 0x48 ^ c_gext[0]
    output[0x13] = 0x45 ^ c_part[0]

    output[0x14] = 0x41 ^ c_cib[1]
    output[0x15] = 0x54 ^ c_soln[1]
    output[0x16] = 0x45 ^ c_gext[1]
    output[0x17] = 0x44 ^ c_part[1]

    output[0x20:0x2C] = b'  RBJ III   ' # no idea what this is, but it seems to be consistent across NYT puzzles

    # "global" checksum
    temp = checksum(0x2c, 8+size*2, 0, output)
    output[:2] = checksum(0, len(partial_board), int.from_bytes(temp, byteorder="little"), partial_board)
    
    with open(save_to, 'wb') as file: # note that 'save_to' includes the directory structure
        file.write(output)
    return(output, partial_board)

fails = scrape_and_puz(date(1942,2,15), date(1993,11,20), overwrite = [False, False], puz_only = False)
