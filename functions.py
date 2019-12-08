#!/usr/bin/python3
# coding=utf-8
# Created by evertonstz
""" This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>. """

import os
import sys
import re
import inspect
import subprocess
import argparse
import hashlib
import configparser
import ctypes
from json import dumps
from shutil import copyfile, which
from csv import DictReader
from math import log2
from sqlitedict import SqliteDict
from platform import system
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit import prompt, HTML, print_formatted_text as printft
from tempfile import TemporaryDirectory as TmpFolder

# local
import variables

##FUNCTIONS##
def get_system():
    return system()

def create_folder(location):
    try:
        os.makedirs(location)
        return True
    except:
        return False

def get_terminal_columns():
    """this function returns the columns' 
    numbers in the terminal"""

    return(os.get_terminal_size().columns)

def is_interactive():
    # Load kernel32.dll
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    # Create an array to store the processes in.  This doesn't actually need to
    # be large enough to store the whole process list since GetConsoleProcessList()
    # just returns the number of processes if the array is too small.
    process_array = (ctypes.c_uint * 1)()
    num_processes = kernel32.GetConsoleProcessList(process_array, 1)
    # num_processes may be 1 if your compiled program doesn't have a launcher/wrapper.
    if num_processes == 2:
        return True
    else:
        return False

def fill_term(symbol="-"):
    """this function fills a line in the 
    terminal with given symbol"""

    return(get_terminal_columns()*symbol)

def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)

def progress_bar(number, symbol="#", fill_width=20, open_symbol="[", close_symbol="]", color=False, unfilled_symbol="-"):
    if color == 0:
        slice = int(number*fill_width/100)
        return(open_symbol+symbol*slice+unfilled_symbol*(fill_width-slice)+close_symbol)
    # else:

    #     slice = int(number*fill_width/100)
    #     if fill_width % 4 == 0:
    #         chunks = int(fill_width/4)
    #         chunks_dir = ""
    #         for i in range(0, slice):
    #             if i in range(0, chunks):
    #                 chunks_dir += LBLUE+symbol
    #             elif i in range(chunks, chunks*2):
    #                 chunks_dir += LGREEN+symbol
    #             elif i in range(chunks*2, chunks*3):
    #                 chunks_dir += YELLOW+symbol
    #             elif i in range(chunks*3, chunks*4):
    #                 chunks_dir += LRED+symbol

    #         return(open_symbol+chunks_dir+GREY+unfilled_symbol*(fill_width-slice)+close_symbol+NC)
    #     else:
    #         print('ERROR: Use a number divisible by 4 in "fill_width".')
    #         sys.exit(1)


def updatedb(dict, system, DBFOLDER, WGET, types):
    """this function downloads the tsvs databases from nps' website"""

    #detect gaming system#
    system_name = variables.FULL_SYSTEM_NAME[system]

    # dict = ['/home/everton/.config/pyNPS/database/PSV/PSV_GAMES.tsv',
    #         '/home/everton/.config/pyNPS/database/PSV/PSV_DLCS.tsv'] #remove

    # db_dict = SqliteDict(_DB, autocommit=False)
    def insert_into_DB(tsv, DB, type):
        with open(tsv, 'r', encoding="utf-8") as file:
            # read source tsv file
            file = [i for i in DictReader(file, delimiter='\t')]

            # write ordered dicsts to new db
        # opens db
        with SqliteDict(DB, autocommit=False) as database:
            #checks for console and make a [] in case it doesn't exist
            if system not in database:
                database[system] = []
            system_database = database[system]
            # if next((item for item in file if item['Title ID'] == "Tom" and item["age"] == 11), None) is not None:
            
            for index_file, i in enumerate(file):
                
                print(f"Processing {type}: {progress_bar( int(index_file/(len(file) - 1) * 100) )}", 
                                            f"({index_file}/{len(file) - 1})", 
                                            end="\r")
                
                i["Type"] = type.upper()
                i['System'] = system
                # check if keys part of the dict are already in the database 'Title ID' 'Region' 'Type' 'System'
                try: 
                    checker = next((item for item in system_database if item['Title ID'] == i['Title ID'] and item['Region'] == i['Region'] and item['System'] == i['System'] and item['Type'] == i['Type'] and item['Content ID'] == i['Content ID']), None)
                except:
                    checker = next((item for item in system_database if item['Title ID'] == i['Title ID'] and item['Region'] == i['Region'] and item['System'] == i['System'] and item['Type'] == i['Type']), None)

                if checker is not None:
                    # this means there's already a entry, only updates the last entry
                    if checker != i:
                        # print("Updated database existing entry:", i['Title ID'], i['Region'], i['Type'], i['System'], i['Name'])
                        checker_index = system_database.index(checker)
                        system_database[checker_index].update(i)
                else:
                    # this means it's a new entry
                    # print("New database entry:", i['Title ID'], i['Region'], i['Type'], i['System'], i['Name'])
                    system_database.append(i)
            print() # escapes \r from print above

            # commit changes
            database[system] = system_database
            database.commit()

    with TmpFolder() as tmp:
        dl_tmp_folder = f"{tmp}/"

        for t in dict:
            if t in types:
                # detect file#
                file = f"{t.upper()}.tsv"
                url = dict[t]

                filename = url.split('/')[-1]

                dl_folder = f"{DBFOLDER}/"

                # create folder
                create_folder(dl_folder)
                process = subprocess.run([WGET, "-q", "--show-progress", url], cwd=dl_tmp_folder)

                #read file and feed to database
                DB = f"{DBFOLDER}/pynps.db"
                insert_into_DB(f"{dl_tmp_folder}{filename}", DB, t) #pass downloaded tsv here in local


def dl_file(dict, system, DLFOLDER, WGET, limit_rate):
    """this function downloads the games"""

    system_name = variables.FULL_SYSTEM_NAME[system.upper()]

    url = dict['PKG direct link']
    filename = url.split('/')[-1]
    name = dict['Name']
    title_id = dict['Title ID']

    printft(HTML("<grey>%s</grey>") %fill_term())
    printft(HTML("<green>[DOWNLOAD] %s (%s) [%s] for %s</green>") %(name, dict['Region'], title_id, system))

    dl_folder = f"{DLFOLDER}/PKG/{system}/{dict['Type']}"

    # making folder
    create_folder(dl_folder)

    # check if file exists
    if os.path.isfile(f"{dl_folder}/{filename}"):
        printft(HTML("<orange>[DOWNLOAD] file exists, wget will decide if the file is completely downloaded, if it's not the download will be resumed</orange>"))

    try:
        if limit_rate is None:
            process = subprocess.run([WGET, "-q", "--show-progress", "-c",
                                    dl_folder, url], cwd=dl_folder)
        else:
            process = subprocess.run([WGET, "-q", "--show-progress", "-c", "--limit-rate", limit_rate,
                                    dl_folder, url], cwd=dl_folder)           
    except KeyboardInterrupt:
        printft(HTML("\n<orange>[DOWNLOAD] File was partially downloaded, you can resume this download by searching for same pkg again</orange>"))
        printft(HTML("<orange>[DOWNLOAD] File location:</orange> <grey>%s/%s</grey>") %(dl_folder, filename))
        printft(HTML("<grey>Download interrupted by user</grey>"))
        sys.exit(0)
    return True


def file_size(size):
    """this function formats bytes into 
    human readable"""

    if type(size) != int:
        try:
            size = int(size)
        except:
            size = 0
    # determine binary order in steps of size 10
    # (coerce to int, // still returns a float)
    order = int(log2(size) / 10) if size else 0
    # format file size
    # (.4g results in rounded numbers for exact matches and max 3 decimals,
    # should never resort to exponent values)
    return '{:.4g} {}'.format(size / (1 << (order * 10)), variables.SUFFIXES[order])


def crop_print(text, leng, center=False, align="left"):
    """this function is helper for process_search()"""

    if len(text) < leng:
        if center == False:
            if align == "left":
                add = (leng-len(text))*" "
                return(f"{text}{add}")
            elif align == "right":
                add = (leng-len(text))*" "
                return(f"{add}{text}")
        else:
            if True:
                add1 = int((leng - len(text)) / 2)
                add2 = (leng - len(text)) - add1
                return(f"{add1*' '}{text}{add2*' '}") 
    elif len(text) == leng:
        return text


def process_search(out):
    """this function prints the search result for the 
    user in a human friendly format"""

    # look for the biggest Index value
    biggest_index = sorted([int(x["Index"]) for x in out])
    lenght_str = len(str(biggest_index[-1]))
    try:
        biggest_type = sorted([len(x['Type']) for x in out])[-1] - 1
    except:
        biggest_type = 2 - 1

    try:
        if sorted([len(x['Region']) for x in out])[-1] in [2, 3]:
            biggest_reg = 3
        elif sorted([len(x['Region']) for x in out])[-1] == 4:
            biggest_reg = 4
    except:
        biggest_reg = 2

    for i in out:
        number_str = crop_print(str(i['Index']), lenght_str)
        system_str = i['System']
        id_str = i['Title ID']

        reg_str = crop_print(variables.REGION_DICT[i['Region']], biggest_reg, center=True)
        type_str = crop_print(variables.TYPE_DICT[i['Type']], biggest_type, center=False)
        size_str = crop_print(file_size(i['File Size']), 9, center=False, align="right")

        head = f"{number_str}) {system_str} | {id_str} | {reg_str} | {type_str} | "

        tail = f" [{size_str}]"

        head_name = f"{head}{i['Name']}"

        term_cols = get_terminal_columns()

        if len(head_name + tail) <= term_cols:  # no neet to crop
            rest = term_cols - len(head_name + tail)
            print(head_name + rest*" " + tail)
        else:
            thats_more = len(head_name + tail) - term_cols

            remove = len(i['Name']) - thats_more

            if remove > 10:
                head_name = head + i['Name'][:remove]
                head_name = head + i['Name'][:remove]
            else:
                head_name = f"{head}{i['Name']}"
            
            print(f"{head_name}{tail}")


def search_db(systems, type, query, region, DBFOLDER):
    """this function searchs in the tsv databases 
    provided by nps"""

    # start = time.time()

    query = query.upper()
    #process query#
    region = [variables.REGION_DICT[x] for x in region]

    DB = f"{DBFOLDER}/pynps.db"

    # parse types to search
    types = [x.upper() for x in type if type[x] == True]
    
    
    # read database
    with SqliteDict(DB, autocommit=False) as database:
        # return everything
        result = []
        for system in systems:
            system_database = database[system]
            if query == "_ALL":
                result = result + [item for item in system_database if 
                                    (item['System'] == system and item['Region'] in region and item['Type'] in types) and
                                    (item['PKG direct link'] not in ["", "MISSING", None, "CART ONLY"])
                                    ]
            else:
                result = result + [item for item in system_database if 
                                    (item['System'] == system and item['Region'] in region and item['Type'] in types) and 
                                    (query.lower() in item['Name'].lower() or query.lower() in item['Title ID']) and
                                    (item['PKG direct link'] not in ["", "MISSING", None, "CART ONLY"])
                                    ]
    # end = time.time()
    # print(end - start)

    # exit()
    return(result)

def checksum_file(file):
    """this fuction is used to calculate a sha256 
    checksum for a file"""

    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    sha256 = hashlib.sha256()

    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return(sha256.hexdigest())


def is_tool(name):
    """Check whether `name` is on PATH and marked 
    as executable."""

    ret = which(name)
    if ret == None:
        return False
    else:
        return ret


def check_wget(location, CONFIGFOLDER):
    """this fuction is used to detect a wget 
    installation in the users system"""

    # check if wget is on path and prefer this one
    if is_tool("wget") != False:
        # can be run as wget
        return(is_tool("wget"))
    else:
        # if not on patch, check if it's on lib and prefer this one
        if os.path.isfile(f"{CONFIGFOLDER}/lib/wget"):
            return(f"{CONFIGFOLDER}/lib/wget")
        else:
            # last resort is check for user provided binary in settings.ini
            # check if exists
            if os.path.isfile(location):
                return(location)
            else:
                return False


def check_pkg2zip(location, CONFIGFOLDER):
    """this function is used to detect a pkg2zip 
    installation in the users system"""

    if is_tool("pkg2zip") != False:
        return(is_tool("pkg2zip"))
    else:
        if os.path.isfile(f"{CONFIGFOLDER}/lib/pkg2zip"):
            return(f"{CONFIGFOLDER}/lib/pkg2zip")
        else:
            if os.path.isfile(location):
                return(location)
            else:
                return False


def run_pkg2zip(file, output_location, PKG2ZIP, args, extraction_folder, zrif=False):  # OK!
    """this fuction is used to extract a pkg with pkg2zip"""
    def runner( list, cwd):

        p = subprocess.Popen(list, cwd=cwd,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT)
        
        r = re.compile('pkg2zip v\\d.\\d')
        full_out = ''
        for line in iter(p.stdout.readline, b''):
            out = line.rstrip().decode()
            full_out += f"{out}\n"
            if out.startswith("ERROR") == False and r.match(out) is None:
                print(out)
        
        # test if file exist
        
        # test for corrupted and file not being a pkg
        if "ERROR: not a pkg file" in full_out:
            # corrupted file and feeding inexistent file
            if os.path.isfile(file):
                if file.endswith(".pkg"):
                    printft(HTML("<red>[PKG2ZIP] The provided file is is a .pkg, but seems to be corrupted</red>"))
                else:
                    printft(HTML("<red>[PKG2ZIP] The provided file is is not a .pkg</red>"))
            else:
                printft(HTML("<red>[PKG2ZIP] Provided file doesn't exist</red>"))
            return False
        elif "ERROR: pkg file is too small" in full_out:
            # download not ended
            printft(HTML("<red>[PKG2ZIP] The provided file is too small, it's probably corrupted or didn't fully downloaded</red>"))
            return False
        elif "ERROR: failed to read 256 bytes from file" in full_out:
            # feeded a folder to pkg2zip
            if os.path.isdir(file):
                printft(HTML("<red>[PKG2ZIP] The provided file seems to be a folder</red>"))
            else:
                printft(HTML("<red>[PKG2ZIP] Unknown extraction error</red>"))
            return False
        else:
            printft(HTML("<green>[PKG2ZIP] File extracted to: </green><grey>%s</grey>") %extraction_folder)
            return True
    
    # create extraction folder
    create_folder(output_location)

    # reversing list
    args.reverse()

    if zrif == False:
        run_lst = [PKG2ZIP, file]
        for x in args:
            run_lst.insert(1, x)
        process = runner(run_lst, cwd=output_location)
    else:
        run_lst = [PKG2ZIP, file, zrif]
        for x in args:
            run_lst.insert(1, x)
        process = runner(run_lst, cwd=output_location)

    return process


def fix_folder_syntax(folder):
    """this function is used to fix slashes in the 
    directories provided by the user's settings.ini"""

    new_folder = folder
    if "\\" in folder:
        new_folder = folder.replace('\\', '/')
    if folder.endswith('/'):
        new_folder = folder[:-1]

    # parsing ./
    if new_folder.startswith("./"):
        new_folder = f"{get_script_dir()}/{new_folder[2:]}"
    return new_folder


def save_conf(file, conf):
    """this function is used to save files"""

    # TODO remove create folder from function!
    create_folder(os.path.dirname(file))
    with open(file, 'w') as file:
        conf.write(file)


def create_config(file, folder):
    """this function is used to create a configuration 
    file on first run"""

    config = configparser.ConfigParser()

    # for linux
    if system() == 'Linux':
        config['pyNPS'] = {'DownloadFolder': folder.replace("/.config/pyNPS", "/Downloads/pyNPS/"), 
                            'DatabaseFolder': f"{folder}/database/"}

        config['BinaryLocations'] = {'Pkg2zip_Location': f"{folder}/lib/pkg2zip",
                                    'Wget_location': f"{folder}/lib/wget"}
    # for windows
    if system() == 'Windows':
        print(11)
        config['pyNPS'] = {'DownloadFolder': './pynps_downloads/', 
                            'DatabaseFolder': "./pynps_database/"}

        config['BinaryLocations'] = {'Pkg2zip_Location': "./pynps_config/lib/pkg2zip.exe",
                                    'Wget_location': "./pynps_config/lib/wget.exe"}
    # for ??
    else:
        config['pyNPS'] = {'DownloadFolder': '', 
                            'DatabaseFolder': ""}

        config['BinaryLocations'] = {'Pkg2zip_Location': "",
                                    'Wget_location': ""}   

    config['PSV_Links'] = variables.CONF_PSV_LINKS
    config['PSP_Links'] = variables.CONF_PSP_LINKS
    config['PSX_Links'] = variables.CONF_PSX_LINKS
    config['PSM_Links'] = variables.CONF_PSM_LINKS
    # saving file
    save_conf(file, config)


def get_theme_folder_name(loc):
    """this function helps to print the exact folder 
    name for extracted PSV themes"""

    a = os.listdir(loc)
    a = sorted([int(x) for x in a])
    comp = list(range(1, a[-1] + 1))
    diff = list(set(comp) - set(a))

    if len(diff) > 0:
        selected = diff[0]
    else:  # == 0
        selected = a[-1] + 1
    # put the zeros in the name 00000005 len = 8
    selected = str(selected)
    zero_lst = [0]*(8 - len(selected))
    return_lst = [str(x) for x in zero_lst]
    return_lst.append(selected)
    return(''.join(return_lst))