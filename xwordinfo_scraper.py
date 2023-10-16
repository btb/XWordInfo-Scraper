import os
import requests
import time
import random
from bs4 import BeautifulSoup
from pprint import pprint

def scrape(min_year=1942, max_year=2023):
    months = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    days = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

    if not os.path.exists('nyt-cw'):
        os.mkdir('nyt-cw')
    os.chdir('nyt-cw')
    
    for y in range(min_year, max_year+1):
        if not os.path.exists(f'{y}'):
            os.mkdir(f'{y}')
        os.chdir(f'{y}')    
        for m in range(1, 13):
            if not os.path.exists(f'{m:0>2}'):
                os.mkdir(f'{m:0>2}')
            os.chdir(f'{m:0>2}')    
            for d in range(1, 32): #days[m]+1):
                filename = f'{months[m]}{d:0>2}{y%100:0>2}.html'
                if os.path.exists(filename):
    #                print('already done')
                    continue
                print(filename)
                URL = f'https://www.xwordinfo.com/PS?date={m}/{d}/{y}'
                start = time.time()
                page = requests.get(URL)
                delay = time.time() - start
    #            print(delay)
                time.sleep(random.uniform(2, 5) * delay)
                if 'No valid puzzle' in page.text  \
                   or 'Puzzles after September 3, 2023 are not available' in page.text \
                   or 'Log in to your XWord Info account' in page.text \
                   or 'not yet available' in page.text \
                   or ("Sunday, February 15, 1942" in page.text and (m, d, y) != (2, 15, 1942)): # don't know why it's pulling in the  first ever puzzle (2/15/42) sometimes, but it is
                    print('DNE')
                    continue
                with open(filename, 'w') as file:
                    file.write(page.text)
                    print('saved')
            os.chdir('..')
        os.chdir('..')
    os.chdir('..')

def checksum(start_bit, length, initial, array):
    cksum = initial

    for i in range(length):
        if cksum & 1:
            cksum = (cksum>>1) + 0x8000
        else:
            cksum = cksum >> 1
        cksum += array[start_bit + i]
    return cksum.to_bytes(2, 'little')

sample = bytearray(b'\x15\x15\x96\x00\x01\x00\x00\x00')

def parse(filename):
    with open(filename, 'r') as file:
        soup = BeautifulSoup(file.read(), "html.parser")

    components = {'filename': filename[:filename.rfind('.')]} # TODO: decide if I need the subfolders

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
            row = '' # separating rows make grids human-readable, for debugging
        cl = square.get("class") or 'None'
        if cl[0] == "black":
            row += '.'
        else:
            if cl != 'None' and cl[0] in ["shade", "bigcircle"]:
                circled.add(i) # used in the GEXT section
            try:
                text = square.find(class_="letter").text
            except AttributeError:
                text = square.text[len(square.find(class_="num").text):]
                if text not in rebuses:
                    rebuses[text] = [i] # rebuses are combined if repeated, will deal with that in the 'GRBS' (grid rebus) and 'RTBL' (rebus table)
                else:
                    rebuses[text].append(i)
            try:
                row += text[0]
            except IndexError:
                raise ValueError("empty cell")
    grid.append(row)

    components['grid'] = grid
    components['rebuses'] = rebuses
    components['circled'] = circled
    components['copyright'] = soup.find(id="CPHContent_Copyright").text
    # components['notes'] = soup.find(id="CPHContent_NotesPan").text.strip() # TODO: maybe dynamically check whether they reference a PDF/alt PUZ
    # this broader version ^ kept too much, often including spoilers. TODO: look into a better way to save these editor notes?
    notes = soup.find(class_="notepad").text.strip()
    if notes.startswith('Notepad: '):
        notes = notes[len('Notepad: '):]
    components['notes'] = notes
    
    author = soup.find(id="CPHContent_AEGrid").text.strip()
    author = author[len('Author:'):]
    author = author.replace('\nEditor:', ' / ')
    components['author'] = author
    try:
        title = soup.find(id="CPHContent_SubTitle").text + ' ' + soup.find(id="PuzTitle").text # TODO: make sure this doesn't break when there isn't a title, just a date
    except AttributeError:
        title = soup.find(id="PuzTitle").text
    components['title'] = title.replace("New York", "NY")

    clues = {'across':{}, 'down': {}}

    across = soup.find(id="ACluesPan").find(class_="numclue").find_all("div")
    i = 0
    while i < len(across):
        clue_num = int(across[i].text) # not sure if I want str or int for this
        clue_text = across[i+1].text
        clue_text = clue_text[:clue_text.rfind(':')-1]
        clues['across'][clue_num] = clue_text
        i += 2

    down = soup.find(id="DCluesPan").find(class_="numclue").find_all("div")
    i = 0
    while i < len(down):
        clue_num = int(down[i].text) # not sure if I want str or int for this
        clue_text = down[i+1].text
        clue_text = clue_text[:clue_text.rfind(':')-1]
        clues['down'][clue_num] = clue_text
        i += 2

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

# sample = bytearray(b'\x15\x15\x96\x00\x01\x00\x00\x00')
# print(checksum(0, 8, 0, sample)) #should get b'\x05\x4E' or b'\x05N'

def build_puz(components):
    output = bytearray(2)
    output.extend([ord(c) for c in 'ACROSS&DOWN\0'])
    output.extend(bytearray(10)) # this and the previous empty space are reserved for checksums
    output.extend(bytearray('1.3\0', encoding='windows-1252'))
    output.extend(bytearray(16)) # hard-coded this later
    output.extend([components['length'], components['width']])
    output.extend(components['num_clues'].to_bytes(2, 'little'))
    output.extend(b'\x01\x00\x00\x00') # more magic numbers? plus more unused scramble

    partial_board = '' # to calculate c_part later

    for line in components['grid']:
        output.extend(bytes(line, encoding='windows-1252'))
    for line in components['grid']:
        # ord('.') == 
        output.extend([45 + (c=='.') for c in line]) # empty grid, 45 for white squares, 46 for black
    for string in [components['title'], components['author'], components['copyright']]:
        output.extend(bytes(string+'\0', encoding='windows-1252')) #.replace(b'\xc2\xa9', b'\xa9'))
        partial_board += (string+'\0')

    # clues
    
    across = components['clues']['across']
    down = components['clues']['down']

    for n in range(1, max(max(across), max(down))+1):
        if n in across:
            output.extend(bytes(across[n]+'\0', encoding="windows-1252"))
            partial_board += across[n]
        if n in down:
            output.extend(bytes(down[n]+'\0', encoding="windows-1252"))
            partial_board += down[n]
    output.extend(bytes(components['notes']+'\0', encoding="windows-1252"))
#    partial_board += '\0'
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
    
    with open(components['filename']+'.puz', 'wb') as file: # note that filename currently includes the directory structure
        file.write(output)
        print(components['filename']+'.puz'+' done')
    return(output, partial_board)

#scrape()

components = parse('nyt-cw/1994/04/Apr0394.html')
    
output, partial = build_puz(components)

#for i in range(0x2c, len(output)):
#    for j in range(i, len(output)):
#        test = checksum(i, j-i, 0, output)
#        if test == b'\xf4\x2b':
#            print(i, j)
