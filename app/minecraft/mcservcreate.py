version = 1
path = ''
pluginask = ''
eulapath = ''
def getinfo():
    global version
    global path
    global pluginask
    global eulapath
    print("Please Choose A Server Version:")
    print("\t 1) 1.15.2 \n",
          "\t 2) 1.14.4 \n",
          "\t 3) 1.13.2 \n",
          "\t 4) 1.12.2 \n")
    version = int(input("Please Enter Your Choice: "))
    path = str(input('Please Enter The Path You Would Like Your Server To Be Located In: '))
    print('Would You Like Us To Add Some Basic Plugins For You? These Consist Of: ')
    print("EssentialsX, EssentialsX Chat, FAWE, ClearLagg, PandaWire")
    pluginask = str(input('Please Enter All If You Would Like Us To Install All The Plugins, Some If You Would Like To Choose What Ones, Or None If You Do Not Want Any Of These Plugins: '))
    pluginask = pluginask.lower()
    if os.name == 'nt':
        eulapath = path + '\eula.txt'
    else:
        eulapath = path + '/eula.txt'
    jar()
def jar():
    global version
    global path
    if os.path.exists(path) == False:
        os.makedirs(path)
    if version == 1:
        print("Downloading 1.15.2 Server Jar")
        url="https://papermc.io/ci/job/Paper-1.15/lastSuccessfulBuild/artifact/paperclip.jar"
        c = urllib3.PoolManager()
        if os.name == 'nt':
            filename = path + "\paperclip.jar"
        else:
            filename = path + "/paperclip.jar"
        with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
            shutil.copyfileobj(res, out_file)
            out_file.close()
    elif version == 2:
        print("Downloading 1.14.4 Server Jar")
        url="https://papermc.io/ci/job/Paper-1.14/lastSuccessfulBuild/artifact/paperclip.jar"
        c = urllib3.PoolManager()
        if os.name == 'nt':
            filename = path + "\paperclip.jar"
        else:
            filename = path + "/paperclip.jar"
        with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
            shutil.copyfileobj(res, out_file)
            out_file.close()
    elif version == 3:
        print("Downloading 1.13.2 Server Jar")
        url="https://papermc.io/ci/job/Paper-1.13/lastSuccessfulBuild/artifact/paperclip.jar"
        c = urllib3.PoolManager()
        if os.name == 'nt':
            filename = path + "\paperclip.jar"
        else:
            filename = path + "/paperclip.jar"
        with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
            shutil.copyfileobj(res, out_file)
            out_file.close()
    else:
        print("Downloading 1.12.2 Server Jar")
        url="https://papermc.io/ci/job/Paper-1.12/lastSuccessfulBuild/artifact/paperclip.jar"
        c = urllib3.PoolManager()
        if os.name == 'nt':
            filename = path + "\paperclip.jar"
        else:
            filename = path + "/paperclip.jar"
        with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
            shutil.copyfileobj(res, out_file)
            out_file.close()
    plugins()
def plugins():
    global path
    global pluginask
    global version
    if pluginask == 'all':
        print("Downloading All Plugins")
        if os.name == 'nt':
            path = path + '\plugins'
            if os.path.exists(path) == False:
                os.makedirs(path)
            url="https://ci.ender.zone/job/EssentialsX/826/artifact/Essentials/target/EssentialsX-2.17.1.62.jar"
            c = urllib3.PoolManager()
            filename = path + "\EssentialsX.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url="https://ci.ender.zone/job/EssentialsX/826/artifact/EssentialsChat/target/EssentialsXChat-2.17.1.62.jar"
            c = urllib3.PoolManager()
            filename = path + "\EssentialsX-Chat.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url = "https://media.forgecdn.net/files/2871/471/Clearlag.jar"
            c = urllib3.PoolManager()
            filename = path + "\Clearlag.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url = "http://files.md-5.net/pandawire/PandaWire-1.15.2.jar"
            c = urllib3.PoolManager()
            filename = path + "\PandaWire.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            if version == '1' or '2':
                url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit-1.15/86/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-86.jar"
                c = urllib3.PoolManager()
                filename = path + "\FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            elif version == '3':
                url = "https://ci.athion.net/job/FastAsyncWorldEdit-1.15/45/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-45.jar"
                c = urllib3.PoolManager()
                filename = path + "\FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            else:
                url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit/1285/artifact/target/FastAsyncWorldEdit-bukkit-19.11.13-5505943-1282-22.3.5.jar"
                c = urllib3.PoolManager()
                filename = path + "\FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
        else:
            path = path + '/plugins'
            if os.path.exists(path) == False:
                os.makedirs(path)
            url = "https://ci.ender.zone/job/EssentialsX/826/artifact/Essentials/target/EssentialsX-2.17.1.62.jar"
            c = urllib3.PoolManager()
            filename = path + "/EssentialsX.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url = "https://ci.ender.zone/job/EssentialsX/826/artifact/EssentialsChat/target/EssentialsXChat-2.17.1.62.jar"
            c = urllib3.PoolManager()
            filename = path + "/EssentialsX-Chat.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url = "https://media.forgecdn.net/files/2871/471/Clearlag.jar"
            c = urllib3.PoolManager()
            filename = path + "/Clearlag.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            url = "http://files.md-5.net/pandawire/PandaWire-1.15.2.jar"
            c = urllib3.PoolManager()
            filename = path + "/PandaWire.jar"
            with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                shutil.copyfileobj(res, out_file)
                out_file.close()
            if version == '1' or '2':
                url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit-1.15/86/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-86.jar"
                c = urllib3.PoolManager()
                filename = path + "/FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            elif version == '3':
                url = "https://ci.athion.net/job/FastAsyncWorldEdit-1.15/45/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-45.jar"
                c = urllib3.PoolManager()
                filename = path + "/FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            else:
                url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit/1285/artifact/target/FastAsyncWorldEdit-bukkit-19.11.13-5505943-1282-22.3.5.jar"
                c = urllib3.PoolManager()
                filename = path + "/FAWE.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
    elif pluginask == 'some':
        print("Please Choose What Plugins You Would Like To Install:")
        if os.name == 'nt':
            path = path + '\plugins'
            if os.path.exists(path) == False:
                os.makedirs(path)
            print("EssentialsX Adds Many Features Such As Being Able To Teleport To Set Locations And More!")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://ci.ender.zone/job/EssentialsX/826/artifact/Essentials/target/EssentialsX-2.17.1.62.jar"
                c = urllib3.PoolManager()
                filename = path + "\EssentialsX.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("EssentialsX Chat Adds The Ability To Talk In Chat With Different Colors!")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://ci.ender.zone/job/EssentialsX/826/artifact/EssentialsChat/target/EssentialsXChat-2.17.1.62.jar"
                c = urllib3.PoolManager()
                filename = path + "\EssentialsX-Chat.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("Clearlag Helps Your Server Run Faster By Removing Entities Like Items Left On The Ground")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://media.forgecdn.net/files/2871/471/Clearlag.jar"
                c = urllib3.PoolManager()
                filename = path + "\Clearlag.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("Pandawire Improves Performance By Optimising Redstone")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "http://files.md-5.net/pandawire/PandaWire-1.15.2.jar"
                c = urllib3.PoolManager()
                filename = path + "\PandaWire.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("FAWE Allows For World Manipulation Through Commands")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                if version == '1' or '2':
                    url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit-1.15/86/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-86.jar"
                    c = urllib3.PoolManager()
                    filename = path + "\FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
                elif version == '3':
                    url = "https://ci.athion.net/job/FastAsyncWorldEdit-1.15/45/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-45.jar"
                    c = urllib3.PoolManager()
                    filename = path + "\FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
                else:
                    url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit/1285/artifact/target/FastAsyncWorldEdit-bukkit-19.11.13-5505943-1282-22.3.5.jar"
                    c = urllib3.PoolManager()
                    filename = path + "\FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
        else:
            path = path + '/plugins'
            if os.path.exists(path) == False:
                os.makedirs(path)
            print("EssentialsX Adds Many Features Such As Being Able To Teleport To Set Locations And More!")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://ci.ender.zone/job/EssentialsX/826/artifact/Essentials/target/EssentialsX-2.17.1.62.jar"
                c = urllib3.PoolManager()
                filename = path + "/EssentialsX.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("EssentialsX Chat Adds The Ability To Talk In Chat With Different Colors!")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://ci.ender.zone/job/EssentialsX/826/artifact/EssentialsChat/target/EssentialsXChat-2.17.1.62.jar"
                c = urllib3.PoolManager()
                filename = path + "/EssentialsX-Chat.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("Clearlag Helps Your Server Run Faster By Removing Entities Like Items Left On The Ground")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "https://media.forgecdn.net/files/2871/471/Clearlag.jar"
                c = urllib3.PoolManager()
                filename = path + "/Clearlag.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("Pandawire Improves Performance By Optimising Redstone")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                url = "http://files.md-5.net/pandawire/PandaWire-1.15.2.jar"
                c = urllib3.PoolManager()
                filename = path + "/PandaWire.jar"
                with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                    shutil.copyfileobj(res, out_file)
                    out_file.close()
            print("FAWE Allows For World Manipulation Through Commands")
            a = input("Would You Like To Install It? [y/n]: ")
            if a == 'y':
                if version == '1' or '2':
                    url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit-1.15/86/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-86.jar"
                    c = urllib3.PoolManager()
                    filename = path + "/FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
                elif version == '3':
                    url = "https://ci.athion.net/job/FastAsyncWorldEdit-1.15/45/artifact/worldedit-bukkit/build/libs/FastAsyncWorldEdit-1.15-45.jar"
                    c = urllib3.PoolManager()
                    filename = path + "/FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
                else:
                    url = "https://ci.athion.net/view/%20%20FastAsyncWorldEdit%20+%20FAVS/job/FastAsyncWorldEdit/1285/artifact/target/FastAsyncWorldEdit-bukkit-19.11.13-5505943-1282-22.3.5.jar"
                    c = urllib3.PoolManager()
                    filename = path + "/FAWE.jar"
                    with c.request('GET', url, preload_content=False) as res, open(filename, 'wb') as out_file:
                        shutil.copyfileobj(res, out_file)
                        out_file.close()
    else:
        print("Not Installing Any Plugins")
    eulagen()
def eulagen():
    global eulapath
    global eulaask
    file = open(eulapath , "w")
    file.write("eula=true")
    file.close()
    end()
def end():
    global path
    print("Please Enter The Following Info Into Crafty:")
    print("\t Path: " + path + "\n \t Server Jar: paperclip.jar ")
import os
import urllib3
import shutil
getinfo()