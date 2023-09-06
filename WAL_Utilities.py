# Travis Reid

import os
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import requests
from surt import surt
import subprocess
import datetime
import json
from warcio.archiveiterator import ArchiveIterator
import pandas as pd
from random import randrange
import audioread
import math
from threading  import Thread
import signal, psutil

class Resource:
    def __init__(self, resourceUrl="", statusCode="", timestamp="", mimeType=""):
        self.resourceUrl = resourceUrl
        self.statusCode = statusCode
        self.timestamp = timestamp
        self.mimeType = mimeType

class MusicTrackInfo:
    def __init__(self, musicDF, songIndex):
        self.title = musicDF["Music Title"][songIndex]
        self.artist = musicDF["Artist"][songIndex]
        self.genre = musicDF["Genre"][songIndex]
        if not pd.isna(musicDF["Mood"][songIndex]):
            self.mood = musicDF
        else:
            self.mood = ""
        if not (pd.isna(musicDF["Music Directory"][songIndex]) or pd.isna(musicDF["File Name"][songIndex])):
            if musicDF["Music Directory"][songIndex][-1] != "/" or musicDF["Music Directory"][songIndex][-1] != "\\":
                self.path = musicDF["Music Directory"][songIndex] + "/" + musicDF["File Name"][songIndex]
            else:
                self.path = musicDF["Music Directory"][songIndex] + musicDF["File Name"][songIndex]
        else:
            self.path = ""
 
class CondensedPerformanceResults:
    def __init__(self, version, resultsDict=None, videoURL="", dateObj=None, dateStr=None, videoOffsetTime=None):
        self.version = version
        self.data = self.getCondensedPerformanceResultsStr(resultsDict)
        self.videoURL = videoURL
        
        if videoOffsetTime != None:
            self.videoURL = self.videoURL + "?t=" + str(videoOffsetTime)
        
        dateFormat = "%Y-%m-%d"
        if dateStr != None:
            self.date = dateStr
        elif dateObj != None:
            self.date = dateObj.strftime(dateFormat)
        else:
            self.date = datetime.datetime.utcnow().strftime(dateFormat)
            
        self.jsonDict = {}
        self.jsonDict["video"] = self.videoURL
        self.jsonDict["v"] = self.version
        self.jsonDict["date"] = self.date
        self.jsonDict["data"] = self.data
        
        self.jsonStr = json.dumps(self.jsonDict)
        
    def getCondensedPerformanceResultsStr(self, resultsDict):
        if resultsDict == None:
            return []
        else:
            data = []
            for rowIndex in range(len(resultsDict["Crawler Name"])):
                data.append([])
                for colIndex in range(len(list(resultsDict.keys()))):
                    key = list(resultsDict.keys())[colIndex]
                    data[rowIndex].append(resultsDict[key][rowIndex])
            print(data)
            return data
    
    def getJsonDict(self):
        return self.jsonDict
    def getJsonStr(self):
        return self.jsonStr

def getDefaultValuesDict():
    defaultValuesDict = {"python_version": "python3", "max_crawl_time": 300, "max_replay_time": 300, "brief_transition_delay": 5, "normal_transition_delay": 10, "replay_web_page_embed_delay":60, "replay_web_page_embed_type": "replayonly", "switch_stage_delay": 15, "load_content_delay": 5, "stage_info_window_height": int(0.157 * 1080), "crawler_info_window_height": int(0.139 * 1920), "stage_info_window_vertical_alignment":"top_window", "crawler_browser_window_vertical_alignment":"center_window", "crawler_info_window_vertical_alignment":"bottom_window", "stage_info_window_horizontal_alignment":"left", "warcprox_port_number":"8081", "warcprox_deduplication_file_path":"warcprox_temp.sqlite", "browsertrix_port_number":"8880", "browsertrix_output_file_option":"--combineWARC", "webis_scriptor_headless":True, "squidwarc_headless": True, "replay_web_page_version": "1.5.11", "replay_web_page_port_number": "8090", "annotate_missing_resources": False, "max_depth_for_frames": 10, "stale_element_delay": 10, "number_of_stale_element_load_attempts": 12, "results_mode_web_page_list":["https://treid003.github.io/WAL_Results.html"], "performance_results_version": "1.1", "metrics_for_scoring": "2,4-25", "delay_between_tracks": 5, "livestream_type_dict":{"archiving_competition":["web_archiving_speedrun", "web_archiving_tournament"], "replay_only":["audit"] }, "prevent_reload_height": 10}
    
    return defaultValuesDict

def clearScreen(driver):
    clearScreenScript = """document.body.innerHTML = "";"""
    driver.execute_script(clearScreenScript)

def getWindowDimensions():
    driver = createGeneralWebDriver()
    driver.maximize_window()
    
    screenWidth = driver.get_window_size()["width"]
    screenHeight = driver.get_window_size()["height"]
    
    driver.close()
    
    return screenWidth, screenHeight

def getCrawlerWindowWidth(livestreamSettings, numCrawlerWindows, appDriver=False, crawlerWindowsGroupLeftMargin=0, crawlerWindowsGroupRightMargin=0, paddingBetweenCrawlerWindows=0, screenWidth=-1):
    
    if crawlerWindowsGroupLeftMargin < 0:
        crawlerWindowsGroupLeftMargin = 0
    
    if crawlerWindowsGroupRightMargin < 0:
        crawlerWindowsGroupRightMargin = 0
    
    if paddingBetweenCrawlerWindows < 0:
        paddingBetweenCrawlerWindows = 0
    
    if screenWidth <= 0:
        screenWidth,screenHeight = getWindowDimensions()
    
    crawlerWidth = ( (screenWidth - crawlerWindowsGroupLeftMargin - crawlerWindowsGroupRightMargin) - (numCrawlerWindows-1) * paddingBetweenCrawlerWindows ) // numCrawlerWindows
    
    if appDriver == False and "browser_window_width_offset" in livestreamSettings:
        crawlerWidth = crawlerWidth + livestreamSettings["browser_window_width_offset"]
    
    return crawlerWidth

def getCrawlerWindowHeight(livestreamSettings, appDriver=False, useCrawlerInfoWindow=True, useStageInfoWindow=True, crawlerInfoWindowHeight=0, stageInfoWindowHeight=0, windowsGroupTopMargin=0, windowsGroupBottomMargin=0, paddingBetweenWindows=0, screenHeight=-1):
    
    if crawlerInfoWindowHeight <= 0:
        if useCrawlerInfoWindow != True:
            crawlerInfoWindowHeight = 0
        else: # Invalid window height
            print("Error in getCrawlerWindowHeight(): The crawlerInfoWindowHeight argument should be set when using the crawler info window")
            exit()
    
    if stageInfoWindowHeight <= 0:
        if useStageInfoWindow != True:
            stageInfoWindowHeight = 0
        else: # Invalid window height
            print("Error in getCrawlerWindowHeight(): The stageInfoWindowHeight argument should be set when using the stage info window")
            exit()
    
    if windowsGroupTopMargin < 0:
         windowsGroupTopMargin = 0
    
    if windowsGroupBottomMargin < 0:
         windowsGroupBottomMargin = 0
    
    if paddingBetweenWindows < 0:
        paddingBetweenWindows = 0
    
    if screenHeight <= 0:
        screenWidth,screenHeight = getWindowDimensions()
    
    '''
    if "web_app_title_bar_height" in livestreamSettings:
        appTitleBarHeight = livestreamSettings["web_app_title_bar_height"]
    else:
        appTitleBarHeight = 0
    '''
    
    if "browser_title_bar_height" in livestreamSettings:
        browserTitleBarHeight = livestreamSettings["browser_title_bar_height"]
    else:
        browserTitleBarHeight = 0
    
    '''
    if "extra_bar_height" in livestreamSettings:
        extraBarHeight = livestreamSettings["extra_bar_height"]
    else:
        extraBarHeight = 0
    '''
    
    numWindows = 1 + useCrawlerInfoWindow + useStageInfoWindow
    
    crawlerHeight = ( (screenHeight - windowsGroupTopMargin - windowsGroupBottomMargin) - (numWindows-1) * paddingBetweenWindows ) - (crawlerInfoWindowHeight * useCrawlerInfoWindow) - (stageInfoWindowHeight * useStageInfoWindow)
    
    if useCrawlerInfoWindow:
        crawlerHeight = crawlerHeight - appTitleBarHeight
    
    if appDriver:
        crawlerHeight = crawlerHeight - appTitleBarHeight - extraBarHeight
        
        if useStageInfoWindow:
            crawlerHeight = crawlerHeight - appTitleBarHeight
        
    #else:
    #crawlerHeight = crawlerHeight - browserTitleBarHeight
    #print(crawlerHeight)
    
    return crawlerHeight

#Window horizontal alignment = "left", "center", or "right"
#Window vertical alignment = "top", "center", or "bottom"
def moveWindow(driver, livestreamSettings, windowWidth, windowHeight, windowHorizontalAlignment, windowVerticalAlignment, appDriver=False, windowX=-1, windowY=-1, leftWindowWidth=0, leftWindowX=0, aboveWindowHeight=0, aboveWindowY=0, windowsGroupLeftMargin=0, windowsGroupRightMargin=0, windowsGroupTopMargin=0, windowsGroupBottomMargin=0, horizontalPaddingBetweenWindows=0, verticalPaddingBetweenWindows=0, screenWidth=-1, screenHeight=-1):

    # Make sure the optional paramaters are set to valid values
    if leftWindowWidth < 0:
       leftWindowWidth = 0
    
    if leftWindowX < 0:
       leftWindowX = 0
    
    if aboveWindowHeight < 0:
       aboveWindowHeight = 0
    
    if aboveWindowY < 0:
       aboveWindowY = 0
    
    if windowsGroupLeftMargin < 0:
       windowsGroupLeftMargin = 0
       
    if windowsGroupRightMargin < 0:
       windowsGroupRightMargin = 0
    
    if windowsGroupTopMargin < 0:
       windowsGroupTopMargin = 0
       
    if windowsGroupBottomMargin < 0:
       windowsGroupBottomMargin = 0

    if horizontalPaddingBetweenWindows < 0:
       horizontalPaddingBetweenWindows = 0

    if verticalPaddingBetweenWindows < 0:
       verticalPaddingBetweenWindows = 0
       
    if screenWidth <= 0 or screenHeight <= 0:
        screenWidth,screenHeight = getWindowDimensions()

    # Determine the x position for the current window
    if windowHorizontalAlignment.lower() == "left":
        if windowX < 0:
            windowX = windowsGroupLeftMargin
    elif windowHorizontalAlignment.lower() == "center":
        if windowX < 0:
            if leftWindowWidth == 0: # invalid width
                print("Error occurred in moveWindow(): The leftWindowWidth argument should be set when placing a window in the center")
                exit()
            else:
                windowX = leftWindowX + leftWindowWidth + horizontalPaddingBetweenWindows
    elif windowHorizontalAlignment.lower() == "right":
        if windowX < 0:
            if leftWindowWidth > 0: # Using left window
                windowX = leftWindowX + leftWindowWidth + horizontalPaddingBetweenWindows
            else: # Using right boundary of the screen
                windowX = screenWidth - windowsGroupRightMargin - windowWidth
    
    
    # Determine the y position for the current window
    if windowVerticalAlignment.lower() == "top":
        if windowY < 0:
            windowY = windowsGroupTopMargin
    elif windowVerticalAlignment.lower() == "center":
        if windowY < 0:
            if aboveWindowHeight == 0: # invalid height
                print("Error occurred in moveWindow(): The aboveWindowHeight argument should be set when placing a window in the center")
                exit()
            else:
                windowY = aboveWindowY + aboveWindowHeight + verticalPaddingBetweenWindows
    elif windowVerticalAlignment.lower() == "bottom":
        if windowY < 0:
            if aboveWindowHeight > 0: # Using above window
                windowY = aboveWindowY + aboveWindowHeight + verticalPaddingBetweenWindows
            else: # Using bottom boundary of the screen
                windowY = screenHeight - windowsGroupBottomMargin - windowHeight
                
    driver.set_window_size(windowWidth, windowHeight)
    
    # May need to set x and y to 1 if an error occurs when placing window at 0
    #'''
    if windowX == 0:
        windowX = 1
    if windowY == 0:
        windowY = 1
    #'''
    
    if "browser_window_y_offset" in livestreamSettings and appDriver == False:
        windowY = windowY + livestreamSettings["browser_window_y_offset"]
        
    if "browser_window_x_offset" in livestreamSettings and appDriver == False:
        if windowHorizontalAlignment.lower() == "left": # leftmost window
            windowX = windowX - livestreamSettings["browser_window_x_offset"]
        else:
            windowX = windowX + livestreamSettings["browser_window_x_offset"]
    
    driver.set_window_position(windowX, windowY)
    
    return windowX,windowY

def setupWindow(windowType, livestreamSettings, defaultValuesDict, windowHorizontalAlignment, windowVerticalAlignment, appDriver=False, windowWidth=0, windowHeight=0, windowX=-1, windowY=-1, leftWindowWidth=0, leftWindowX=0, aboveWindowHeight=0, aboveWindowY=0, windowsGroupLeftMargin=0, windowsGroupRightMargin=0, windowsGroupTopMargin=0, windowsGroupBottomMargin=0, horizontalPaddingBetweenWindows=0, verticalPaddingBetweenWindows=0, displayAllCrawlerWindows=True, extraBrowserWindows=0, screenWidth=-1, screenHeight=-1):
    
    defaultCrawlerInfoWindowHeight = defaultValuesDict["crawler_info_window_height"] #170 or 15.7% of screen height
    defaultStageInfoWindowHeight = defaultValuesDict["stage_info_window_height"] #150 or 13.9% of screen height

    if screenWidth <= 0 or screenHeight <= 0:
        screenWidth,screenHeight = getWindowDimensions()

    if extraBrowserWindows < 0:
        extraBrowserWindows = 0

    if windowsGroupLeftMargin <= 0:
        if "left_margin" in livestreamSettings:
            windowsGroupLeftMargin = livestreamSettings["left_margin"]
        else:
            windowsGroupLeftMargin = 0
            
    if windowsGroupRightMargin <= 0:
        if "right_margin" in livestreamSettings:
            windowsGroupRightMargin = livestreamSettings["right_margin"]
        else:
            windowsGroupRightMargin = 0
            
    if windowsGroupTopMargin <= 0:
        if "top_margin" in livestreamSettings:
            windowsGroupTopMargin = livestreamSettings["top_margin"]
        else:
            windowsGroupTopMargin = 0
            
    if windowsGroupBottomMargin <= 0:
        if "bottom_margin" in livestreamSettings:
            windowsGroupBottomMargin = livestreamSettings["bottom_margin"]
        else:
            windowsGroupBottomMargin = 0
            
    if horizontalPaddingBetweenWindows <= 0:
        if "horizontal_padding_between_windows" in livestreamSettings:
            horizontalPaddingBetweenWindows = livestreamSettings["horizontal_padding_between_windows"]
        else:
            horizontalPaddingBetweenWindows = 0
            
    if verticalPaddingBetweenWindows <= 0:
        if "vertical_padding_between_windows" in livestreamSettings:
            verticalPaddingBetweenWindows = livestreamSettings["vertical_padding_between_windows"]
        else:
            verticalPaddingBetweenWindows = 0

    if "use_crawler_info_window" in livestreamSettings:
        useCrawlerInfoWindow = livestreamSettings["use_crawler_info_window"]
    else:
        useCrawlerInfoWindow = True
        
    if "use_stage_info_window" in livestreamSettings:
        useStageInfoWindow = livestreamSettings["use_stage_info_window"]
    else:
        useStageInfoWindow = True

    if "stage_info_window_width" in livestreamSettings:
        stageInfoWindowWidth = livestreamSettings["stage_info_window_width"]
    else:
        stageInfoWindowWidth = screenWidth * useStageInfoWindow
    
    if "stage_info_window_height" in livestreamSettings:
        stageInfoWindowHeight = livestreamSettings["stage_info_window_height"]
    else:
        stageInfoWindowHeight = defaultStageInfoWindowHeight * useStageInfoWindow

    crawlerBrowserWindowWidth = getCrawlerWindowWidth(livestreamSettings, livestreamSettings["num_crawlers"] + extraBrowserWindows, appDriver=appDriver, crawlerWindowsGroupLeftMargin=windowsGroupLeftMargin, crawlerWindowsGroupRightMargin=windowsGroupRightMargin, paddingBetweenCrawlerWindows=horizontalPaddingBetweenWindows, screenWidth=screenWidth)

    if "crawler_info_window_width" in livestreamSettings:
        crawlerInfoWindowWidth = livestreamSettings["crawler_info_window_width"]
    else:
        crawlerInfoWindowWidth = crawlerBrowserWindowWidth * useCrawlerInfoWindow

    if "crawler_info_window_height" in livestreamSettings:
        crawlerInfoWindowHeight = livestreamSettings["crawler_info_window_height"]
    else:
        crawlerInfoWindowHeight = defaultCrawlerInfoWindowHeight * useCrawlerInfoWindow
    
    crawlerBrowserWindowHeight = getCrawlerWindowHeight(livestreamSettings, appDriver=appDriver, useCrawlerInfoWindow=useCrawlerInfoWindow, useStageInfoWindow=useStageInfoWindow, crawlerInfoWindowHeight=crawlerInfoWindowHeight, stageInfoWindowHeight=stageInfoWindowHeight, windowsGroupTopMargin=windowsGroupTopMargin, windowsGroupBottomMargin=windowsGroupBottomMargin, paddingBetweenWindows=verticalPaddingBetweenWindows, screenHeight=screenHeight)
    #print(stageInfoWindowHeight, crawlerInfoWindowHeight, crawlerBrowserWindowHeight)
    
    if windowType.lower() == "stage_info_window":
        title = "Current Stage Info"
        windowDriver = getAppDriver(title, muteAudio=False)
        
        if windowWidth <= 0:
            windowWidth = stageInfoWindowWidth
        
        if windowHeight <= 0:
            windowHeight = stageInfoWindowHeight
        
    elif windowType.lower() == "crawler_info_window":
        title = "Crawler Info"
        windowDriver = getAppDriver(title)

        if windowWidth <= 0:
            windowWidth = crawlerInfoWindowWidth
                
        if windowHeight <= 0:
            windowHeight = crawlerInfoWindowHeight
    
    elif windowType.lower() == "crawler_browser_window":
        if appDriver == False:
            windowDriver = createGeneralWebDriver()
        else:
            title = "Command Output"
            windowDriver = getAppDriver(title)
        
        if windowWidth <= 0:
            windowWidth = crawlerBrowserWindowWidth
                
        if windowHeight <= 0:
            windowHeight = crawlerBrowserWindowHeight
    
    elif windowType.lower() == "replay_info_window":
        title = "Info Window"
        windowDriver = getAppDriver(title)
        
        if windowWidth <= 0:
            if extraBrowserWindows > 0:
                windowWidth = crawlerBrowserWindowWidth
            elif displayAllCrawlerWindows == False:
                windowWidth = screenWidth // 2
                
        if windowHeight <= 0:
            windowHeight = crawlerInfoWindowHeight
    elif windowType.lower() == "replay_browser_window":
        #windowDriver = createGeneralWebDriver()
        title = "Browser Window"
        windowDriver = getAppDriver(title)
        
        if windowWidth <= 0:
            if extraBrowserWindows > 0:
                windowWidth = crawlerBrowserWindowWidth
            elif displayAllCrawlerWindows == False:
                windowWidth = screenWidth // 2
                
        if windowHeight <= 0:
            windowHeight = crawlerBrowserWindowHeight
        
        

        
    moveWindow(windowDriver, livestreamSettings, windowWidth, windowHeight, windowHorizontalAlignment, windowVerticalAlignment, appDriver=appDriver, windowX=windowX, windowY=windowY, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, aboveWindowHeight=aboveWindowHeight, aboveWindowY=aboveWindowY, windowsGroupLeftMargin=windowsGroupLeftMargin, windowsGroupRightMargin=windowsGroupRightMargin, windowsGroupTopMargin=windowsGroupTopMargin, windowsGroupBottomMargin=windowsGroupBottomMargin, horizontalPaddingBetweenWindows=horizontalPaddingBetweenWindows, verticalPaddingBetweenWindows=verticalPaddingBetweenWindows, screenWidth=screenWidth, screenHeight=screenHeight)
    
    return windowDriver

# Return an updated file name and path based on its creation time
def getUpdatedFileNameAndPath(oldFileName, oldFilePath):
    dateTimeFormat = "%Y_%m_%d_%H_%M_%S"
    seconds = os.path.getctime(oldFilePath)
    timeStamp = time.ctime(seconds)
    timeObj = time.strptime(timeStamp)
    timeStamp = time.strftime(dateTimeFormat, timeObj)
    newFileName = timeStamp + "_" + oldFileName
    temp = oldFilePath.rsplit(oldFileName, 1)
    newFilePath = newFileName.join(temp)
    
    return newFileName, newFilePath

# This function finds all of the files that need to be renamed before the speedrun begins
def renamePrevFiles(livestreamSettings, modeList):
    prevResultFilesList = []
    
    if "result_files_directory" in livestreamSettings:
        resultsDir = livestreamSettings["result_files_directory"]
    else:
        resultsDir = os.path.abspath(os.getcwd())
    
    if "results mode" in modeList:
        if "web_archiving_livestream_results_file_name" in livestreamSettings:
            prevResultFilesList.append(livestreamSettings["web_archiving_livestream_results_file_name"])
            prevResultFilesList.append(livestreamSettings["web_archiving_livestream_results_file_name"].replace(".csv", "_per_web_page.csv"))
        else:
            prevResultFilesList.append("web_archiving_livestream_results.csv")
            prevResultFilesList.append("web_archiving_livestream_results_per_web_page.csv")
        
    for prevFileName in prevResultFilesList:
        prevFilePath = resultsDir + "/" + prevFileName
        if os.path.exists(prevFilePath):
            # Rename the file based on its creation time
            newFileName, newFilePath = getUpdatedFileNameAndPath(prevFileName, prevFilePath)
            os.rename(prevFilePath, newFilePath)
            

def deleteDuplicateMusicFiles(removeDuplicateMusicList):
    for musicFile in removeDuplicateMusicList:
        os.remove(musicFile)

def signalHandler(signum, frame):
    raise Exception("A statement took too long")

def killProcess(process):
    try:
        parentProcess = psutil.Process(process.pid)
        children = parentProcess.children(recursive=True)
        for childProcess in children:
            childProcess.send_signal(signal.SIGKILL)
        process.kill()
    except:
        print("")

def stopProcess(process):
    try:
        parentProcess = psutil.Process(process.pid)
        children = parentProcess.children(recursive=True)
        for childProcess in children:
            childProcess.send_signal(signal.SIGINT)
        parentProcess.send_signal(signal.SIGINT)
    except:
        print("")


def terminateProcess(process, maxWaitTime=60):
    try:
        parentProcess = psutil.Process(process.pid)
        children = parentProcess.children(recursive=True)
        for childProcess in children:
            childProcess.send_signal(signal.SIGTERM)
        process.terminate()
        # Give the process a few seconds to shut down
        waitTime = 0
        while process.poll() is None and waitTime < maxWaitTime:
            time.sleep(1)
            waitTime = waitTime + 1
        killProcess(process)
    except:
        print("")

def startSimpleServer(livestreamSettings, defaultValuesDict):
    if "replay_web_page_port_number" in livestreamSettings:
        portNum = livestreamSettings["replay_web_page_port_number"]
    else:
        portNum = defaultValuesDict["replay_web_page_port_number"]
    
    simpleServerProcess = subprocess.Popen([defaultValuesDict["python_version"], '-m', 'http.server', portNum])
    
    return simpleServerProcess

def checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre="all", prevMusicIndexList=None, delayBetweenTracks=5):
    if willPlayMusic and not isMusicPlaying(musicDriver):
        if musicInfo != None:
            musicPathList = [musicInfo.path]
            
            if os.getcwd() != os.path.dirname(musicInfo.path): # Need to update this condition
                deleteDuplicateMusicFiles(musicPathList)
        else:
            musicPathList = []

        musicInfo, musicDuration = changeMusic(musicDF, musicDriver, currentGenre, musicPathList, prevMusicIndexList=prevMusicIndexList, localServerPortNum=localServerPortNum, delayBetweenTracks=delayBetweenTracks)
    else:
        musicInfo = None
        musicDuration = 0
    return musicInfo, musicDuration

def createGeneralWebDriver(driverOptions=None, muteAudio=True):
    if driverOptions == None:
        # Remove automation message
        driverOptions = Options()
        driverOptions.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    if muteAudio:
        driverOptions.add_argument("--mute-audio")
    
    hasOpenedBrowser = False
    while not hasOpenedBrowser:
        try:
            #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=driverOptions)
            #driver = webdriver.Chrome(service=Service(ChromeDriverManager(version="114.0.5735.90").install()), options=driverOptions)
            driver = webdriver.Chrome(options=driverOptions)
            hasOpenedBrowser = True
        except:
            continue
    
    return driver
    
def getAppDriver(title, muteAudio=True):
    blankPageCode="""<html><head><title>%s</title></head><body style="overflow: hidden;"></body></html>"""%(title)
    appValue = "data:text/html," + blankPageCode

    driverOptions = Options()
    driverOptions.add_argument("--app=" + appValue)
    driverOptions.add_experimental_option("excludeSwitches", ["enable-automation"])

    appDriver = createGeneralWebDriver(driverOptions=driverOptions, muteAudio=muteAudio)
    
    return appDriver

def setupCommandWindow(crawlerName, crawlerNameList, crawlerBrowserDriverList):
    currentIndex = crawlerNameList.index(crawlerName)
    initialWindowScript = """
    document.body.style.backgroundColor = "black";
    var command = document.createElement("h1");
    command.id = "command";
    command.style.color = "white";
    var beginLine = "> ";
    command.innerHTML = beginLine;
    document.body.appendChild(command);

    var outputLine = document.createElement("h1");
    outputLine.id = "command_output";
    outputLine.style.color = "white";
    document.body.appendChild(outputLine);
    """
    crawlerBrowserDriverList[currentIndex].execute_script(initialWindowScript)

def printNextLineForCommand(outputObj, driver): #commandProcess, outputType, crawlerName
    # Print next line for the command's output
    ## Acquire a lock before printing the output for the command
    #processLocksDict[crawlerName]["crawler_output"].acquire() #processLocksDict,
    '''
    if outputType == "stderr":
        line = commandProcess.stderr.readline()
    else:
        line = commandProcess.stdout.readline()
    '''
    try:
        line = outputObj.readline()
    except:
        line = None
    if line != None and line != "":
        line = line.decode(errors="backslashreplace")
        line = line.replace('"', '\\"').replace("'", "\\'").replace("‘", "\\‘").replace("’", "\\’").replace("\n", "<br>")
        
        try:
            updateOutput = """
            var outputLine = document.getElementById("command_output");
            outputLine.innerHTML = outputLine.innerHTML + "%s";
            """%(line)
            driver.execute_script(updateOutput)
            scrollWebPageToBottomNoDelay(driver)
        except:
            line = None
    
    # Release the lock
    #processLocksDict[crawlerName]["crawler_output"].release()

def startPrintNextLineProcess(name, driver, outputObj, currentThread):
    if currentThread != None and currentThread.is_alive() == False:
        #currentThread.join()
        currentThread = None
        '''
        try:
            sys.exit()
        except:
            currentThread = None
        '''
    
    if currentThread == None:
            currentThread = Thread(target=printNextLineForCommand, args=(outputObj, driver))
            currentThread.daemon  = True
            currentThread.start()
        
    return currentThread

def getScoringMetricList(scoringMetricsStr):
    scoringMetricsList = scoringMetricsStr.split(",") # Get most of the scoring metrics that are not in a range
    tempList = []
    for scoringMetric in scoringMetricsList:
        if "-" in scoringMetric:
            beginningIndex = int(scoringMetric.split("-")[0])
            endIndex = int(scoringMetric.split("-")[-1])
            for metricIndex in range(beginningIndex, endIndex + 1):
                tempList.append(str(metricIndex))
        else:
            tempList.append(scoringMetric)
    scoringMetricsList = tempList
    return scoringMetricsList

def getNumScoringMetrics(scoringMetricsStr):
    return len(getScoringMetricList(scoringMetricsStr))

def isAttributePresent(element, attribute):
    try:
        element.get_attribute(attribute)
        return True
    except:
        return False


def canSwitchToFrame(driver, frameType, frameIndex, allCapturedURIsList):
    try:
        frame = driver.find_elements(By.TAG_NAME, frameType)[frameIndex]
        if frame.get_attribute("src") not in allCapturedURIsList:
            return False
        else:
            return True
    except:
        return False
        
def getFrameIndex(driver, frame):
    frameList = driver.find_elements(By.TAG_NAME, "iframe")
    for index in range(len(frameList)):
        if frame == frameList[index]:
            return index
    
    # Return an invalid index when frame is no longer accessible
    return -1


def switchToReplayIframe(driver, replaySystem, loadTimeout=120):
    
    hasSwitchedToFrame = False
    
    startLoadTime = datetime.datetime.utcnow()
    
    driver.switch_to.default_content() #Switch to default content first
    
    ## Check if the WARC file is missing
    title = None
    title = driver.execute_script("""if(document.getElementsByTagName("title").length == 1) {return document.getElementsByTagName("title")[0].innerHTML;} else{return ""}""")
    title = title.lower()
    #print('"' + title + '"')
    if "missing" in title and "file" in title:
        return False
    
    
    # Get the scripts that are associated
    if replaySystem.lower() == "replayweb.page":
        getOuterIframeScript="""
        replayWebPage = document.getElementsByTagName("replay-web-page")[0];
        tempShadow = replayWebPage.shadowRoot;
        outerIframe = tempShadow.querySelectorAll("iframe")[0];
        return outerIframe
        """
        
        getReplayIframeScript="""
        outerIframe = document;
        tempShadow = outerIframe.getElementsByTagName("replay-app-main")[0].shadowRoot;
        appEmbed = tempShadow.querySelectorAll("wr-coll")[0]
        tempShadow = appEmbed.shadowRoot.getElementById("replay").shadowRoot;
        replayIframe = tempShadow.querySelectorAll("iframe.iframe-main")[0];
        return replayIframe;
        """
        
        ## Have to go through a shadow root before getting the replay iframe for ReplayWeb.page
        ### Wait until the ReplayWeb.page has loaded
        loadTimeDuration = 0
        haveLoadedElement = False
        while loadTimeDuration < loadTimeout and not haveLoadedElement:
            try:
                title = None
                title = driver.execute_script("""if(document.getElementsByTagName("title").length == 1) {return document.getElementsByTagName("title")[0].innerHTML;} else{return ""}""")
                if title != None:
                    title = title.lower()
                    if "missing" in title and "file" in title:
                        return False
                driver.find_elements(By.TAG_NAME, "replay-web-page")[0] #Check if the element is available
                outerIframe = driver.execute_script(getOuterIframeScript) #Get the iframe to switch to
                WebDriverWait(driver, 1).until(EC.frame_to_be_available_and_switch_to_it(outerIframe)) #Switch to iframe
                haveLoadedElement = True
            except:
                haveLoadedElement = False
            
            loadTimeDuration = int( (datetime.datetime.utcnow() - startLoadTime).total_seconds() )
        
        ## Try to load the replay iframe
        loadTimeDuration = int( (datetime.datetime.utcnow() - startLoadTime).total_seconds() )
        haveLoadedElement = False
        while loadTimeDuration < loadTimeout and not haveLoadedElement:
            try:
                title = None
                title = driver.execute_script("""if(document.getElementsByTagName("title").length == 1) {return document.getElementsByTagName("title")[0].innerHTML;} else{return ""}""")
                if title != None:
                    title = title.lower()
                    if "missing" in title and "file" in title:
                        return False
                driver.find_elements(By.TAG_NAME, "replay-app-main")[0] #Check if the element is available
                replayIframe = driver.execute_script(getReplayIframeScript) #Get the iframe to switch to
                WebDriverWait(driver, 1).until(EC.frame_to_be_available_and_switch_to_it(replayIframe)) #Switch to iframe
                haveLoadedElement = True
            except:
                haveLoadedElement = False
            
            loadTimeDuration = int( (datetime.datetime.utcnow() - startLoadTime).total_seconds() )
        
        hasSwitchedToFrame = haveLoadedElement
    else:
        print("Error occurred when switching to the replay frame: The replay system being used is not supported yet")
        exit()

    loadTimeDuration = int( (datetime.datetime.utcnow() - startLoadTime).total_seconds() )
    #print("Load time: " + str(loadTimeDuration))
    return hasSwitchedToFrame


# This function was created for the case where switching to a parent frame using driver.switch_to.parent_frame() and driver.switch_to.frame(element.parent) causes stale element errors
## The framePathList should be the path to the frame that will be switched to and each element of the list should be an index to a frame. The driver will start at the frame for the archived web page and then use the framePathList to reach the frame
def switchToFrame(driver, replaySystem, framePathList=None, timeout=0, frameType="iframe"):

    hasSwitchedToFrame = switchToReplayIframe(driver, replaySystem)
    
    if framePathList != None and hasSwitchedToFrame:
        for i in range(len(framePathList)):
            frameIndex = framePathList[i]
            try:
                driver.switch_to.frame(frameIndex)
            except:
                #Get Parent element
                if len(framePathList) > 1:
                    switchToFrame(driver, replaySystem, framePathList=framePathList[:-1], timeout=0)
                else:
                    switchToFrame(driver, replaySystem, framePathList=None, timeout=0)
                #Get the frame element if it still exists
                frameList = driver.find_elements(By.TAG_NAME, frameType)
                if len(framePathList) > frameIndex:
                    frame = frameList[frameIndex]
                    #Switch to child frame
                    WebDriverWait(driver, timeout).until(EC.frame_to_be_available_and_switch_to_it(frame))
                else:
                    hasSwitchedToFrame = False
    
    return hasSwitchedToFrame

def getScrollHeight(driver):
    #getScrollHeightScript_1 = """return document.body.scrollHeight"""
    scrollHeight_1 = driver.execute_script("""return document.body.scrollHeight;""")
    scrollHeight_2 = driver.execute_script("""return document.documentElement.scrollHeight;""")
    scrollHeight_3 = driver.execute_script("""return window.innerHeight;""")
    scrollHeight = max(scrollHeight_1, scrollHeight_2, scrollHeight_3)
    #print(scrollHeight)
    return scrollHeight

def getSortedScrollableElementsList(driver):
    getSortedScrollableElementsListScript = """
    allElementsArray = Array.from(document.querySelectorAll("*"));
    
    //Get the scrollable elements and all frames
    scrollThreshold = 100;
    allScrollableElements = [];
    for(const element of allElementsArray)
    {
        if(element.scrollHeight > (element.clientHeight + scrollThreshold)  || element.tagName.toLowerCase() == "iframe" || element.tagName.toLowerCase() == "frame")
        {
            allScrollableElements.push(element);
        }
    }
    
    //Sort the list of scrollable elements based on the top position of the client rect for the element
    for(let i = 0; i < allScrollableElements.length; i++)
    {
        minIndex = i;
        for(let j = i + 1; j < allScrollableElements.length; j++)
        {
            if(allScrollableElements[j].getBoundingClientRect().top < allScrollableElements[minIndex].getBoundingClientRect().top)
            {
                minIndex = j;
            }
        }
        
        //Swap elements if necessary
        if(minIndex != i)
        {
            temp =  allScrollableElements[i];
            allScrollableElements[i] = allScrollableElements[minIndex];
            allScrollableElements[minIndex] = temp;
        }
    }
    
    return allScrollableElements;
    """
    
    sortedScrollableElementsList = driver.execute_script(getSortedScrollableElementsListScript)
    
    return sortedScrollableElementsList


def scrollElementToBottom(driver, element, scrollFrames=True, annotateElements=False, allCapturedURIsList=None, maxFrameDepth=10, staleElementDelay=12, numStaleElementLoadAttemps=10, framePathList=None, willPlayMusic=False, musicDriver=None, musicDF=None, musicInfo=None, localServerPortNum=None, currentMusicGenre="all", prevMusicIndexList=None, delayBetweenTracks=0, scrollTimeout=300, startScrollTime=None):
    # Check if a timeout should occur
    if startScrollTime == None:
        startScrollTime = datetime.datetime.utcnow()
    scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
    if scrollTimeDuration >= scrollTimeout:
        return True # Exit this function and return True so that the element will not be scrolled again
    
    if framePathList == None:
        framePathList = []
        
    try:
        if element.tag_name.lower() == "html" or element.is_displayed() == False:
            return True
        
        getScrollHeightScript = """return arguments[0].scrollHeight"""
        getScrollWidthScript = """return arguments[0].scrollWidth"""
        currentLiveScrollHeight = driver.execute_script(getScrollHeightScript, element)
        currentLiveScrollWidth = driver.execute_script(getScrollWidthScript, element)
            
        driver.execute_script("""arguments[0].scrollIntoView()""", element)
        driver.execute_script("""if(window.scrollY > 100){window.scrollBy(0, -100)}""") # Scroll above the element, because there could be a menu covering part of the element
        
        if element.tag_name.lower() != "frame" and element.tag_name.lower() != "iframe":
            scrollDownScript = """arguments[0].scrollBy(0, 1)"""
            previousLiveScrollHeight = -1
            verticalPosition = 0
            loadDelay = 2
            finished = False
            while not finished:
                scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
                if verticalPosition < currentLiveScrollHeight:
                    driver.execute_script(scrollDownScript, element)
                    verticalPosition = verticalPosition + 1
                elif verticalPosition == currentLiveScrollHeight and previousLiveScrollHeight != currentLiveScrollHeight:
                    ### Delay before getting the current scroll height
                    previousLiveScrollHeight = currentLiveScrollHeight
                    time.sleep(loadDelay)
                elif previousLiveScrollHeight == currentLiveScrollHeight or scrollTimeDuration >= scrollTimeout:
                    finished = True
                
                musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
                
                currentLiveScrollHeight = driver.execute_script(getScrollHeightScript, element)
            
            #Scroll to the top of the element, because in some cases the content for the element disappears when it reaches the bottom
            driver.execute_script("""arguments[0].scrollTo(0,0);""", element)
            
        elif scrollFrames and maxFrameDepth > 0:
            ## Get Attributes that may become stale when switching to a different frame
            hasScrollingElement = isAttributePresent(element, "scrolling")
            if hasScrollingElement == True:
                scrollingValue = element.get_attribute("scrolling").lower()
            else:
                scrollingValue = "null"
            
            ## When the current element is a frame or iframe
            ##Get the frame index for this new frame
            frameIndex = getFrameIndex(driver, element)
            
            loadElementTimeout = staleElementDelay * numStaleElementLoadAttemps
            currentLoadAttempt = 1
            haveLoadedElement = False
            while currentLoadAttempt <= numStaleElementLoadAttemps and (not haveLoadedElement) and (scrollTimeDuration + staleElementDelay) < scrollTimeout:
                try:
                    WebDriverWait(driver, staleElementDelay).until(EC.frame_to_be_available_and_switch_to_it(element)) #Need to switch to the frame in order to scroll the frame
                    haveLoadedElement = True
                except:
                    currentLoadAttempt = currentLoadAttempt + 1
                    scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
            
            framePathList.append(frameIndex)
            if framePathList == -1:
                ### The frame has been removed from the DOM, has become stale, or the frame has been recently modified.
                #### Set the nextFrameDepth to 0 to make sure the recursive function call does not attept to switch to a child frame for the current frame
                nextFrameDepth = 0
            else:
                nextFrameDepth = maxFrameDepth - 1

            if scrollingValue != "no":
                scrollPageToBottom(driver, scrollFrames=scrollFrames, maxFrameDepth=nextFrameDepth, framePathList=framePathList, willPlayMusic=willPlayMusic, musicDriver=musicDriver, musicDF=musicDF, musicInfo=musicInfo, localServerPortNum=localServerPortNum, currentMusicGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks, scrollTimeout=scrollTimeout, startScrollTime=startScrollTime)
            else:
                # When the frame cannot be scrolled, only scroll the elements in the frame
                finishedScrolling = False
                prevScrollableElementsList = []
                loadElementTime = 0
                while not finishedScrolling and loadElementTime <= loadElementTimeout:
                    finishedScrolling = True
                    try:
                        sortedScrollableElementsList = getSortedScrollableElementsList(driver)

                        for currentElement in sortedScrollableElementsList:
                            if currentElement not in prevScrollableElementsList:
                                finishedScrolling = scrollElementToBottom(driver, currentElement, scrollFrames=True, annotateElements=annotateElements, allCapturedURIsList=allCapturedURIsList, maxFrameDepth=nextFrameDepth, framePathList=framePathList, willPlayMusic=willPlayMusic, musicDriver=musicDriver, musicDF=musicDF, musicInfo=musicInfo, localServerPortNum=localServerPortNum, currentMusicGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks, scrollTimeout=scrollTimeout, startScrollTime=startScrollTime)
                                if finishedScrolling:
                                    loadElementTime = 0 # Reset the time for the next element
                                prevScrollableElementsList.append(currentElement)
                    except:
                        finishedScrolling = False
                        loadElementTime = loadElementTime + 1
                        time.sleep(1)
                    
                    musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)

            driver.execute_script("""window.scrollTo(0,0);""")
            # Switch back to the current frame
            if framePathList != None and len(framePathList) >= 1:
                framePathList.pop()
            switchToFrame(driver, replaySystem, framePathList=framePathList)
        
        return True
    except:
        print("Exception prevented scrolling iframe")
        return False


def scrollPageToBottom(driver, initialXpos=0, initialYpos=0, scrollFrames=True, maxFrameDepth=10, framePathList=None, willPlayMusic=False, musicDriver=None, musicDF=None, musicInfo=None, localServerPortNum=None, currentMusicGenre="all", prevMusicIndexList=None, delayBetweenTracks=0, scrollTimeout=300, startScrollTime=None):
    # Check if a timeout should occur
    if startScrollTime == None:
        startScrollTime = datetime.datetime.utcnow()
    scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
    if scrollTimeDuration >= scrollTimeout:
        return # Exit this function
    
    if framePathList == None:
        framePathList = []
    
    getScrollHeightScript = """return document.body.scrollHeight"""
    getScrollWidthScript = """return document.body.scrollWidth"""
    currentLiveScrollHeight = driver.execute_script(getScrollHeightScript)
    currentLiveScrollWidth = driver.execute_script(getScrollWidthScript)
    
    if initialXpos < 0:
        initialXpos = 0
    elif initialXpos > currentLiveScrollWidth:
        initialXpos = currentLiveScrollWidth
    
    if initialYpos < 0:
        initialYpos = 0
    elif initialYpos > currentLiveScrollHeight:
        initialYpos = currentLiveScrollWidth
        
    driver.execute_script("""window.scrollTo(%s,%s);"""%(initialXpos, initialYpos)) # Make the page go to initial position
    
    scrollDownScript = """window.scrollBy(0, 1)"""
    previousLiveScrollHeight = -1
    verticalPosition = 0
    loadDelay = 2
    finished = False
    while not finished:
        scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
        ## Scroll web page
        if verticalPosition < currentLiveScrollHeight:
            driver.execute_script(scrollDownScript)
            verticalPosition = verticalPosition + 1
        elif verticalPosition >= currentLiveScrollHeight and previousLiveScrollHeight != currentLiveScrollHeight:
            ### Delay before getting the current scroll height
            previousLiveScrollHeight = currentLiveScrollHeight
            time.sleep(loadDelay)
        elif previousLiveScrollHeight == currentLiveScrollHeight or scrollTimeDuration >= scrollTimeout:
            finished = True
        
        musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
        
        currentLiveScrollHeight = driver.execute_script(getScrollHeightScript)
    
    if scrollFrames:
        finishedScrolling = False
        prevScrollableElementsList = []
        while not finishedScrolling:
            finishedScrolling = True
            try:
                sortedScrollableElementsList = getSortedScrollableElementsList(driver)
                for currentElementIndex in range(len(sortedScrollableElementsList)):
                    currentElement = sortedScrollableElementsList[currentElementIndex]
                    if currentElementIndex not in prevScrollableElementsList:
                        finishedScrolling = scrollElementToBottom(driver, currentElement, scrollFrames=True, maxFrameDepth=maxFrameDepth, framePathList=framePathList, willPlayMusic=willPlayMusic, musicDriver=musicDriver, musicDF=musicDF, musicInfo=musicInfo, localServerPortNum=localServerPortNum, currentMusicGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks, scrollTimeout=scrollTimeout, startScrollTime=startScrollTime)
                        prevScrollableElementsList.append(currentElementIndex) #Changed to element index, because elements could be modified by JavaScript which may cause problems with comparing elements
            except:
                finishedScrolling = False
            
            musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)


def scrollPageToBottomWithDelay(driver, switchFrame=False, replaySystem="", switchFrameAfterScroll=False, delayAfterScroll=5, scrollFrames=False, maxFrameDepth=10, framePathList=None, willPlayMusic=False, musicDriver=None, musicDF=None, musicInfo=None, localServerPortNum=None, currentMusicGenre="all", prevMusicIndexList=None, delayBetweenTracks=0):
    if framePathList == None:
        framePathList = []
    
    if switchFrame:
        switchToFrame(driver, replaySystem, framePathList=framePathList)
        
    scrollPageToBottom(driver, scrollFrames=scrollFrames, maxFrameDepth=maxFrameDepth, framePathList=framePathList, willPlayMusic=willPlayMusic, musicDriver=musicDriver, musicDF=musicDF, musicInfo=musicInfo, localServerPortNum=localServerPortNum, currentMusicGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
    
    if delayAfterScroll > 0:
        time.sleep(delayAfterScroll)
    
    #Scroll to the top of the page, because in some cases the content for the frame disappears when it reaches the bottom (Example: an embedded Twitter feed)
    driver.execute_script("""window.scrollTo(0,0);""")
    
    if switchFrameAfterScroll:
        switchToFrame(driver, replaySystem, framePathList=framePathList)

# Need to use a different approach to get resource URIs (do not delete this function, may reuse the code for switching between iframes)
def getResourceURIs(driver, scrollPage=False, switchFrame=False, replaySystem="", switchFrameAfterScroll=False, delayAfterScroll=5, recursive=False, maxDepth=5, staleElementDelay=12, numStaleElementLoadAttemps=10, framePathList=None):

    if framePathList == None:
        framePathList = []
    
    if scrollPage:
        scrollPageToBottomWithDelay(driver, switchFrame=switchFrame, replaySystem=replaySystem, switchFrameAfterScroll=switchFrameAfterScroll, delayAfterScroll=delayAfterScroll, scrollFrames=True, framePathList=framePathList, prevMusicIndexList=prevMusicIndexList,)
    elif switchFrame:
        switchToFrame(driver, replaySystem, framePathList=framePathList)
    
    getResourceURIsScript ="""
    function isMalformedURL(currentURI)
    {
        try
        {
            currentURI = new URL(currentURI, document.baseURI).href;
            return false;
        }
        catch(e)
        {
            return true;
        }
        return true;
    }

    //Check the attribute list for elements that contain src like the data-src or data-bgsrc attributes
    //srcset can have multiple src values that are seperated by commas, so make sure to split the srcset by "," when checking the list of src values in a WARC file
    // Also need to have a special case for handling iframes that use srcdoc instead of src. srcdoc attribute is used when embeding the HTML source directly into the iframe instead of referencing an external webpage.
    allElementsNodeList = document.querySelectorAll("*");
    const resourceURIArray = [];
    for(const element of allElementsNodeList)
    {
        for(const attribute of element.attributes)
        {
            attributeName = attribute.localName;
            if(attributeName.includes("src") && attributeName != "srcdoc" && attributeName != "srclang")
            {
                if(attributeName == "src")
                {
                    currentURI = new URL(element.getAttribute(attributeName), document.baseURI).href;
                    if(!resourceURIArray.includes(currentURI))
                        resourceURIArray.push(currentURI);
                }
                else if(attributeName == "srcset")
                {
                    srcSet = element.getAttribute(attributeName);
                    // Check if there are any commas in the URLs
                    if(srcSet.split(",").length == srcSet.split(/[x,|w,]/))
                    {
                        for(const srcSetElement of srcSet.split(","))
                        {
                            srcSetUri = new URL(srcSetElement.trim().split(" ")[0], document.baseURI).href;
                            if(!resourceURIArray.includes(srcSetUri))
                                resourceURIArray.push(srcSetUri);
                        }
                    }
                    else
                    { //When there are commas in one or more URLs
                        const srcSetArray = srcSet.trim().replace(/\s+,/g, ",").split(/\s+/);
                        currentIndex = 0;
                        currentIsContentDescriptor = false;
                        prevIsContentDescriptor = false;
                        while(currentIndex < srcSetArray.length)
                        {
                            //Check if the element is the condition descriptor for an image
                            if( ( (srcSetArray[currentIndex].endsWith("x,") || srcSetArray[currentIndex].endsWith("w,")) && !isNaN(srcSetArray[currentIndex].split(/x,|w,/)[0]) ) || ( currentIndex == srcSetArray.length - 1 && (srcSetArray[currentIndex].endsWith("x") || srcSetArray[currentIndex].endsWith("w")) && !isNaN(srcSetArray[currentIndex].split(/x|w/)[0])) )
                            {
                                if(prevIsContentDescriptor || currentIndex == 0)
                                { ///When a image file is named like a content descriptor
                                    srcSetUri = new URL(srcSetArray[currentIndex], document.baseURI).href;
                                    if(!resourceURIArray.includes(srcSetUri))
                                        resourceURIArray.push(srcSetUri);
                                    currentIsContentDescriptor = false;
                                }
                                else
                                {
                                    ///Check if the current element also contains the next URL
                                    if(srcSetArray[currentIndex].split(/x,|w,/).length == 2 && srcSetArray[currentIndex].split(/x,|w,/)[1] != "")
                                    {
                                        srcSetUri = new URL(srcSetArray[currentIndex], document.baseURI).href;
                                        if(!resourceURIArray.includes(srcSetUri))
                                            resourceURIArray.push(srcSetUri);
                                        currentIsContentDescriptor = false;
                                    }
                                    else
                                    {
                                        currentIsContentDescriptor = true;
                                    }
                                }
                            }
                            else
                            {///When the current element is a URL
                                srcSetUri = new URL(srcSetArray[currentIndex], document.baseURI).href;
                                if(!resourceURIArray.includes(srcSetUri))
                                    resourceURIArray.push(srcSetUri);
                                currentIsContentDescriptor = false;
                            }
                            
                            //Remove extra comma from previous URI if necessary
                            if(currentIndex > 0 && !prevIsContentDescriptor && !currentIsContentDescriptor && resourceURIArray[resourceURIArray.length - 1].endsWith(","))
                            {
                                previousURI = resourceURIArray[resourceURIArray.length - 1];
                                previousURI = previousURI.substring(0, previousURI.length - 1);
                                resourceURIArray[resourceURIArray.length - 1] = previousURI;
                            }
                            prevIsContentDescriptor = currentIsContentDescriptor;
                            currentIndex = currentIndex + 1;
                        }
                    }
                }
                else
                {
                    currentURI = new URL(element.getAttribute(attributeName), document.baseURI).href;
                    if(!isMalformedURL(currentURI) && !resourceURIArray.includes(currentURI))
                        resourceURIArray.push(currentURI);
                }
            }
            else if(element.tagName == "link" && attributeName == "href")
            {
                currentURI = new URL(element.getAttribute(attributeName), document.baseURI).href;
                if(!resourceURIArray.includes(currentURI))
                    resourceURIArray.push(currentURI);
            }
        }
    }

    return resourceURIArray;
    """
    try:
        allResourceURIsList = driver.execute_script(getResourceURIsScript)
    except:
        allResourceURIsList = None
        print("Exception occurred when getting the resource URIs")
        return []
    
    #Recursive call to iframes
    loadElementTimeout = staleElementDelay * numStaleElementLoadAttemps
    
    if recursive == True and maxDepth >= 1:
        finished = False
        prevFrames = []
        loadElementTime = 0
        while not finished and loadElementTime <= loadElementTimeout:
            switchToFrame(driver, replaySystem, framePathList=framePathList)
            finished = True
            try:
                #frameList = driver.execute_script(getFramesScript)
                frameList = driver.find_elements(By.TAG_NAME, "iframe")
                #frameList = driver.find_element(By.CSS_SELECTOR, "#modal > iframe")
                for frameIndex in range(len(frameList)):
                    frame = frameList[frameIndex]
                    if frameIndex not in prevFrames:
                        #print(driver.execute_script("return document.body").get_attribute("outerHTML"))
                        # Switch to parent frame
                        switchToFrame(driver, replaySystem, framePathList=framePathList)
                        
                        # Switch to child frame
                        ## Scroll the child frame into view
                        driver.execute_script("""arguments[0].scrollIntoView()""", frame)
                        WebDriverWait(driver, loadElementTimeout).until(EC.frame_to_be_available_and_switch_to_it(frame))
                        
                        framePathList.append(frameIndex)
                        
                        currentResourceURIsList = driver.execute_script(getResourceURIsScript)
                        
                        allResourceURIsList.extend(currentResourceURIsList)
                        
                        prevFrames.append(frameIndex)
                        
                        # Finished with the current frame and will switch back to parent frame during next iteration
                        framePathList.pop()
                        
                        loadElementTime = 0 # Reset the time for the next frame
                        
            except:
                finished = False
                loadElementTime = loadElementTime + 1
                time.sleep(1)
    #'''
    #Make sure the driver is set to the first frame used by this function
    switchToFrame(driver, replaySystem, framePathList=framePathList)
    
    return allResourceURIsList


def annotateMissingResources(driver, replaySystem, allCapturedURIsList, recursive=False, maxDepth=5, staleElementDelay=12, numStaleElementLoadAttemps=10, framePathList=None):
    if framePathList == None:
        framePathList = []
        
    #Scroll to the top of the frame
    driver.execute_script("""window.scrollTo(0,0)""")
    
    annotateMissingResourcesScript ="""
    replaySystem = "%s";

    /// ** Need to update the annotate element function to handle the case where some alternative image URLs or video URLs are captured so that it prints the correct annotation

    // Pausing 5 seconds in JavaScript: https://stackoverflow.com/questions/14226803/wait-5-seconds-before-executing-next-line
    const delay = ms => new Promise(res => setTimeout(res, ms));
    function annotateElement(elementToAnnotate, currentURL, extraScrollByY=0) {
        borderWidth = 5;
        annotateEntireViewport = false;
        distanceBetweenAnnotationBoxes = 100;
        
        //Get dimensions of the resource and the x, y, and z positions
        elementToAnnotate.scrollIntoView();
        if(extraScrollByY != 0)
        {
            window.scrollBy(0, extraScrollByY);
        }
        elementRect = elementToAnnotate.getBoundingClientRect();
        //*
        //Change elementRect for elements that are empty set the elementRect to the parent element's rect or body's rect
        /// There could be a special case for iframe
        elementTagName = elementToAnnotate.tagName.toLowerCase();
        if(elementTagName == "source" || elementTagName == "track")
        {
            parentToAnnotate = elementToAnnotate.parentElement;
            elementRect = parentToAnnotate.getBoundingClientRect();
            while( (elementRect.width *  elementRect.height) == 0 && (parentToAnnotate != document.body) )
            {
                parentToAnnotate = parentToAnnotate.parentElement;
                elementRect = parentToAnnotate.getBoundingClientRect();
            }
            
            if(parentToAnnotate == document.body)
            {
                annotateEntireViewport = true;
            }
        }
        //*
        else if(elementTagName == "script" || elementTagName == "link" || (elementRect.width == 0 || elementRect.height == 0) )
        {
            annotateEntireViewport = true;
        }
        
        bodyRect = document.body.getBoundingClientRect();
        if(!annotateEntireViewport)
        {
            centerOfElementX = elementRect.left + elementRect.width / 2;
            centerOfElementY = elementRect.top + elementRect.height / 2;
            annotationSquareWidth = (elementRect.width + borderWidth * 4);
            annotationSquareHeight = (elementRect.height + borderWidth * 4);
            annotationSquareX = Math.round( (centerOfElementX - (annotationSquareWidth/2)) - bodyRect.left - borderWidth * 1); //
            annotationSquareY = Math.round( (centerOfElementY - (annotationSquareHeight/2)) - bodyRect.top - borderWidth * 1); //
            bgColor = "transparent";
            opacity = "1.0";
            annotationTextWS = 'normal';
            borderDivRadius = "5px";
        }
        else
        {
            width = document.body.clientWidth;
            
            if(document.body.clientWidth < document.body.scrollWidth)
            {
                height = window.innerHeight - (document.body.scrollWidth - document.body.clientWidth);
            }
            else
            {
                height = window.innerHeight;
            }
            
            elementRect = new DOMRect(0, 0, width, height);

            annotationSquareWidth = elementRect.width - borderWidth;
            annotationSquareHeight = elementRect.height - borderWidth;
            annotationSquareX =  Math.trunc(elementRect.left - bodyRect.left);
            annotationSquareY = Math.trunc(elementRect.top - bodyRect.top);
            bgColor = "grey";
            opacity = "0.50";
            annotationTextWS = 'normal';///'nowrap';
            borderDivRadius = "0px";
        }
        //*/
        
        var annotationDiv = document.createElement("div");
        annotationDiv.id = "temp_annotation";
        document.body.appendChild(annotationDiv);
        annotationDiv.style.display = "inline-block";
        annotationDiv.style.width = annotationSquareWidth.toString() + "px";
        annotationDiv.style.height = annotationSquareHeight.toString() + "px";

        annotationDiv.style.position = "absolute";
        annotationDiv.style.left = annotationSquareX.toString() + "px" ;
        annotationDiv.style.top = annotationSquareY.toString() + "px" ;

        annotationDiv.style.borderStyle = "solid";
        annotationDiv.style.borderWidth = borderWidth.toString() + "px";
        annotationDiv.style.borderColor = "red";
        annotationDiv.style.borderRadius = borderDivRadius;
        
        annotationDiv.style.backgroundColor = bgColor;
        annotationDiv.style.opacity = opacity;
        
        
        
        var annotationText = document.createElement("div");
        annotationText.id = "temp_annotation_text";
        document.body.appendChild(annotationText);
        annotationText.style.display = "inline-block";
        annotationText.style.position = "absolute";

        annotationText.style.borderStyle = "solid";
        annotationText.style.borderWidth = borderWidth.toString() + "px";
        annotationText.style.borderColor = "red";
        annotationText.style.borderRadius = "5px";
        
        annotationText.style.backgroundColor = "white";
        
        var descriptionLine = document.createElement("p");
        descriptionLine.innerHTML = "The URI for this < " + elementToAnnotate.tagName.toLowerCase() + " > element was not archived";
        descriptionLine.style.textAlign = "center";
        descriptionLine.id = "temp_annotation_description_line";
        descriptionLine.style.fontSize = "24px";
        descriptionLine.style.whiteSpace = annotationTextWS;
        descriptionLine.style.overflowWrap = 'break-word';
        //descriptionLine.style.lineHeight = '2.09vw';
        annotationText.appendChild(descriptionLine);
        
        var urlLine = document.createElement("p");
        urlLine.style.textAlign = "center";
        urlLine.innerHTML = "<b>URI</b>: " + currentURL;
        urlLine.id = "temp_annotation_url_line";
        urlLine.style.fontSize = "24px";
        urlLine.style.whiteSpace = annotationTextWS;
        urlLine.style.overflowWrap = 'break-word';
        //urlLine.style.lineHeight = '2.09vw';
        annotationText.appendChild(urlLine);
        
        if(!annotateEntireViewport)
        {
            // annotationTextWidth = min(leftSideSpace, rightSideSpace);
            /// annotationTextWidth = min(annotationSquare_X_center, viewportWidth - annotationSquare_X_center);
            centerOfAnnotationSquareX = annotationSquareX + annotationSquareWidth / 2;
            annotationTextWidth = Math.min(centerOfAnnotationSquareX, document.body.clientWidth - centerOfAnnotationSquareX);
            annotationTextX = centerOfAnnotationSquareX - (annotationTextWidth / 2);
            annotationTextY = Math.trunc(annotationSquareY + annotationSquareHeight + distanceBetweenAnnotationBoxes);
            
            annotationText.style.width = annotationTextWidth.toString() + "px";
        }
        else
        {
            annotationTextWidth = Math.max(descriptionLine.getBoundingClientRect().width, urlLine.getBoundingClientRect().width);
            annotationTextX = Math.round(elementRect.width/2 - bodyRect.left);
            annotationTextY = Math.round(elementRect.height/2 - bodyRect.top);
        }
        //annotationText.style.width = annotationTextWidth.toString() + "px";
        //annotationTextHeight = Math.trunc(descriptionLine.getBoundingClientRect().height + urlLine.getBoundingClientRect().height);
        annotationTextHeight = annotationText.getBoundingClientRect().height;
        //annotationText.style.height = annotationTextHeight.toString() + "px";
        annotationText.style.padding = "20px";
        
        
        if(!annotateEntireViewport)
        {
            annotationText.style.left = annotationTextX.toString() + "px" ;
            annotationText.style.top = annotationTextY.toString() + "px" ;
        }
        else
        {
            annotationText.style.left = ( Math.round(annotationTextX - annotationTextWidth/2) ).toString() + "px" ;
            annotationText.style.top = ( Math.round(annotationTextY - annotationTextHeight/2) ).toString() + "px" ;
        }
        
        
    }

    //Check the attribute list for elements that contain src like the data-src or data-bgsrc attributes
    //srcset can have multiple src values that are seperated by commas, so make sure to split the srcset by "," when checking the list of src values in a WARC file
    // Also need to have a special case for handling iframes that use srcdoc instead of src. srcdoc attribute is used when embeding the HTML source directly into the iframe instead of referencing an external webpage.
    allElementsNodeList = document.querySelectorAll("*");
    const attributesWithsrcArray = [];
    attributesWithsrcStr = "";
    for(const element of allElementsNodeList)
    {
        for(const attribute of element.attributes)
        {
            attributeName = attribute.localName;
            if(attributeName.includes("src") && !attributesWithsrcArray.includes(attributeName) && attributeName != "srcdoc" && attributeName != "srclang")
            {
                attributesWithsrcArray.push(attributeName);
                attributesWithsrcStr = attributesWithsrcStr + "[" + attributeName + "], ";
            }
        }
    }
    attributesWithsrcStr = attributesWithsrcStr.substring(0, attributesWithsrcStr.length - 2);
    otherCSSselectors = "link[rel='stylesheet']";
    queryString = otherCSSselectors + ", " + attributesWithsrcStr;
    //Example resources that should be included: "link[rel='stylesheet'], script[src], audio[src], source[src], source[srcset], track[src], input[src], img[src], embed[src], video[src], iframe[src], frame[src]"
    resourcesNodeList = document.querySelectorAll(queryString);
    //resourcesNodeList = document.querySelectorAll("link[rel='stylesheet'], script[src], audio[src], source[src], source[srcset], track[src], input[src], img[src], embed[src], video[src], iframe[src], frame[src]");

    const capturedResourceURLsArray = %s;
    console.log(capturedResourceURLsArray);
    console.log(attributesWithsrcArray);
    function isMalformedURL(currentURI)
    {
        try
        {
            currentURI = new URL(currentURI, document.baseURI).href;
            return false;
        }
        catch(e)
        {
            return true;
        }
        return true;
    }

    function isArchived(capturedResourceURLsArray, currentURI, replaySystem)
    {console.log(currentURI); //console.log(capturedResourceURLsArray);
        ///Need to update the annotate element function to handle the case where some alternative image URLs or video URLs are captured so that it prints the correct annotation
        try
        {
            currentURI = new URL(currentURI, document.baseURI).href;
            if(replaySystem.toLowerCase() == "replayweb.page")
            {
                if(currentURI.includes("about:blank"))
                {   ///Should exclude about:blank
                    currentURI = "excluded";
                    return "invalid";
                }
                else if(currentURI.includes("/replay/"))
                {
                    currentURI = currentURI.replace("&amp;", "&");
                    if(currentURI.split("http").length > 2)
                    {
                        //Get the URI-R and see if it is in the list of captured resource URI list
                        currentURI = "http" + currentURI.split("http").slice(2, currentURI.length).join("http");
                    }
                    else
                    {
                        currentURI = "excluded";
                        return "invalid";
                    }
                }
            }
            
            if( !capturedResourceURLsArray.includes(currentURI) && currentURI != "excluded")
            {
                console.log(currentURI);
                return "false";
            }
            else
            {
                return "true";
            }
        }
        catch(e)
        {
            return "false";
        }
        
        return "false";
    }

    function getAnnotationList(resourcesNodeList, replaySystem)
    {
        // for ... of loop: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...of
        annotationList = []
        for(const node of resourcesNodeList)
        {
            willAnnotateElement = false;
            currentTagName = node.tagName.toLowerCase();
            //*
            if(currentTagName == "link")
            {
                currentURI = node.href.trim();
                if(isArchived(capturedResourceURLsArray, currentURI, replaySystem) == "false" && !isMalformedURL(currentURI))
                {
                    annotationList.push({"element": node, "URI": currentURI});
                }
            }
            else
            {
                for(const attribute of node.attributes)
                {
                    attributeName = attribute.localName;
                    if(attributesWithsrcArray.includes(attributeName))
                    {
                        currentURI = node.getAttribute(attributeName).trim();
                        if(isArchived(capturedResourceURLsArray, currentURI, replaySystem) == "false" && !isMalformedURL(currentURI))
                        {
                            annotationList.push({"element": node, "URI": currentURI});
                            break;
                        }
                    }
                }
            }
        }
        return annotationList;
    }
    
    const annotateElements = async (annotationList) => {
        window.scrollTo(0,0);
        for(let i = 0; i < annotationList.length; i++)
        {
            element = annotationList[i]["element"];
            currentURI = annotationList[i]["URI"];
            element.scrollIntoView();
            await delay(1000);
            annotateElement(element, currentURI, -100); // -100
            await delay(10000);
            document.getElementById("temp_annotation").remove();
            document.getElementById("temp_annotation_text").remove();
            await delay(2000);
        }
    };

    const annotateAllMissingResources = async (resourcesNodeList, replaySystem) => {

        window.scrollTo(0,0);
        // for ... of loop: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...of
        for(const node of resourcesNodeList)
        {
            willAnnotateElement = false;
            currentTagName = node.tagName.toLowerCase();
            //*
            if(currentTagName == "link")
            {
                currentURI = node.href.trim();
                if(isArchived(capturedResourceURLsArray, currentURI, replaySystem) == "false" && !isMalformedURL(currentURI))
                {
                    willAnnotateElement = true;
                }
            }
            else
            {
                for(const attribute of node.attributes)
                {
                    attributeName = attribute.localName;
                    if(attributesWithsrcArray.includes(attributeName))
                    {
                        currentURI = node.getAttribute(attributeName).trim();
                        if(isArchived(capturedResourceURLsArray, currentURI, replaySystem) == "false" && !isMalformedURL(currentURI))
                        {
                            willAnnotateElement = true;
                            break;
                        }
                    }
                }
            }
            //*/
            if(willAnnotateElement)
            {
                node.scrollIntoView();
                await delay(1000);
                annotateElement(node, currentURI);
                await delay(10000);
                document.getElementById("temp_annotation").remove();
                document.getElementById("temp_annotation_text").remove();
                await delay(2000);
            }
        }
    };

    //annotateAllMissingResources(resourcesNodeList, replaySystem);
    annotationList = getAnnotationList(resourcesNodeList, replaySystem);
    annotateElements(annotationList);

    //return queryString;
    return annotationList;

    """%(replaySystem, str(allCapturedURIsList))

    annotationList = driver.execute_script(annotateMissingResourcesScript)

    annotationDelay = 14 # Based on the awaits statements in the annotation script
    time.sleep(len(annotationList) * annotationDelay)
    
    
    loadElementTimeout = staleElementDelay * numStaleElementLoadAttemps
    if recursive == True and maxDepth >= 1:
        finished = False
        prevFrames = []
        loadElementTime = 0
        while not finished and loadElementTime <= loadElementTimeout:
            switchToFrame(driver, replaySystem, framePathList=framePathList)
            finished = True
            try:
                frameList = driver.find_elements(By.TAG_NAME, "iframe")

                for index in range(len(frameList)):
                    frame = frameList[index]
                    if frame not in prevFrames:
                        prevFrames.append(frame)

                        # Switch to parent frame
                        switchToFrame(driver, replaySystem, framePathList=framePathList)
                        frame = driver.find_elements(By.TAG_NAME, "iframe")[index]
                        
                        # Switch to child frame
                        ## Continue to the next frame if it is not possible to switch to the child frame
                        prevFrameCode = driver.execute_script("return document.body").get_attribute("innerHTML")
                        ## Scroll the child frame into view
                        driver.execute_script("""arguments[0].scrollIntoView()""", frame)

                        WebDriverWait(driver, loadElementTimeout).until(EC.frame_to_be_available_and_switch_to_it(frame))
                        currentFrameCode = driver.execute_script("return document.body").get_attribute("innerHTML")

                        if prevFrameCode == currentFrameCode:
                            continue # If the frame did not change move to the next child frame
                            
                        framePathList.append(index)
                        currentAnnotationList = annotateMissingResources(driver, replaySystem, allCapturedURIsList, recursive=True, maxDepth=(maxDepth-1), staleElementDelay=staleElementDelay, numStaleElementLoadAttemps=numStaleElementLoadAttemps, framePathList=framePathList)
                        
                        annotationList.extend(currentAnnotationList)
                        
                        # Finished with the current frame and will switch back to parent frame during next iteration
                        framePathList.pop()
                        
                        loadElementTime = 0 # Reset the time for the next frame
                        
            except:
                print("Exception for frame: " + str(framePathList))
                finished = False
                loadElementTime = loadElementTime + 1
                time.sleep(1)
    #'''
    
    return annotationList


def annotateFrames(driver, replaySystem, allCapturedURIsList, recursive=False, maxDepth=5, staleElementDelay=12, numStaleElementLoadAttemps=10, framePathList=None):
    #Recursive call to iframes
    annotationList = []
    loadElementTimeout = staleElementDelay * numStaleElementLoadAttemps
    if recursive == True and maxDepth >= 1:
        finished = False
        canSwitch = True
        prevFrames = []
        while not finished:
            finished = True
            try:
                frameList = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frameList:
                    frameIndex = frameList.index(frame)
                    if frame not in prevFrames and canSwitchToFrame(driver, "iframe", frameList.index(frame), allCapturedURIsList):
                        driver.execute_script("""arguments[0].scrollIntoView()""", frame)
                        framePathList.append(frameIndex)
                        switchToFrame(driver, replaySystem, framePathList=framePathList, timeout=loadElementTimeout)
                        print(driver.execute_script("return document.body").get_attribute("outerHTML").split("\n")[0])

                        currentAnnotationList = annotateMissingResources(driver, replaySystem, allCapturedURIsList, recursive=False, maxDepth=(maxDepth-1), staleElementDelay=staleElementDelay, numStaleElementLoadAttemps=numStaleElementLoadAttemps, framePathList=framePathList)
                        annotationList.extend(currentAnnotationList)
                        framePathList.pop()
                        switchToFrame(driver, replaySystem, framePathList=framePathList)
                        prevFrames.append(frame)
            except:
                print("Unexpected error thrown")
                finished = False
    return annotationList


def getMissingResourcesListFromFramesAndShadowDOMs(driver, livestreamSettings, replaySystem, warcFilePath, scrollFrames=False, annotateElements=False, allCapturedURIsList=None, maxDepth=5, staleElementDelay=12, numStaleElementLoadAttemps=10, framePathList=None):
    if framePathList == None:
        framePathList = []
    
    getFramesScript = """
    const frameArray = Array.from(document.getElementsByTagName("frame"));
    const iframeArray = Array.from(document.getElementsByTagName("iframe"));
    const allFramesArray = frameArray.concat(iframeArray);
    
    //Scroll to the top of each frame
    for(const frame of allFramesArray)
    {
       frame.scrollIntoView();
       frame.scrollTo(0,0);
    }
    
    return allFramesArray;
    """
    numFrames = driver.execute_script("""return document.getElementsByTagName("frame").length + document.getElementsByTagName("iframe").length""")
    switchToFrame(driver, replaySystem, framePathList=framePathList)
    frameList = driver.find_elements(By.TAG_NAME, "iframe")
    missingResourcesList = []
    capturedResourcesList = []
    if len(frameList) <= 0 or maxDepth < 1:
        return missingResourcesList, capturedResourcesList
    
    loadElementTimeout = staleElementDelay * numStaleElementLoadAttemps
    if maxDepth >= 1:
        finished = False
        prevFrames = []
        loadElementTime = 0
        while not finished and loadElementTime <= loadElementTimeout:
            switchToFrame(driver, replaySystem, framePathList=framePathList)
            finished = True
            try:
                frameList = driver.find_elements(By.TAG_NAME, "iframe")
                for index in range(len(frameList)):
                    frame = frameList[index]
                    if frame not in prevFrames:
                        # Switch to parent frame
                        switchToFrame(driver, replaySystem, framePathList=framePathList)
                        
                        # Switch to child frame
                        ## Scroll the child frame into view
                        driver.execute_script("""arguments[0].scrollIntoView()""", frame)
                        WebDriverWait(driver, loadElementTimeout).until(EC.frame_to_be_available_and_switch_to_it(frame))
                        
                        framePathList.append(index)
                        
                        # Do not scroll the frame or annotate the elments, because it should have been scrolled and annotated before by the scrollElementToBottom function
                        currentMissingResourcesList, currentCapturedResourcesList = getMissingResourcesListDuringReplay(driver, livestreamSettings, replaySystem, warcFilePath, scrollPage=False, annotateElements=annotateElements, allCapturedURIsList=allCapturedURIsList, maxDepth=(maxDepth-1))
                        
                        missingResourcesList.extend(currentMissingResourcesList)
                        capturedResourcesList.extend(currentCapturedResourcesList)
                        
                        # Recursively call this function so that it goes through all nested frames
                        childrenMissingResourcesList, childrenCapturedResourcesList = getMissingResourcesListFromFramesAndShadowDOMs(driver, livestreamSettings, replaySystem, warcFilePath, scrollFrames=scrollFrames, annotateElements=annotateElements, allCapturedURIsList=allCapturedURIsList, maxDepth=(maxDepth-1), staleElementDelay=staleElementDelay, numStaleElementLoadAttemps=numStaleElementLoadAttemps, framePathList=framePathList)
                        
                        missingResourcesList.extend(childrenMissingResourcesList)
                        capturedResourcesList.extend(childrenCapturedResourcesList)
                        
                        prevFrames.append(frame)
                        
                        # Finished with the current frame and will switch back to parent frame during next iteration
                        framePathList.pop()
                        
                        loadElementTime = 0 # Reset the time for the next frame
                        
            except:
                finished = False
                loadElementTime = loadElementTime + 1
                time.sleep(1)
    
    #Make sure the driver is set to the first frame used by this function
    switchToFrame(driver, replaySystem, framePathList=framePathList)
    
    #Remove duplicates from missingResourcesList (ordering of elements will change)
    missingResourcesList = [*set(missingResourcesList)]
    capturedResourcesList = [*set(capturedResourcesList)]
    return missingResourcesList, capturedResourcesList


def getCapturedURLs(warcFilePath):
    if not os.path.exists(warcFilePath):
        return []
        
    allCapturedURIsList = []
    with open(warcFilePath, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == "response":
                targetURI = record.rec_headers.get_header('WARC-Target-URI')
                if int(record.http_headers.get_statuscode()) < 400:
                    if not(targetURI in allCapturedURIsList):
                        allCapturedURIsList.append(targetURI)
    return allCapturedURIsList


# Need to use a different approach to get resource URIs
def getMissingResourcesListDuringReplay(driver, livestreamSettings, replaySystem, warcFilePath, scrollPage=False, annotateElements=False, allCapturedURIsList=None, maxDepth=5, framePathList=None):
    if framePathList == None:
        framePathList = []
    
    if "delay_after_scroll" in livestreamSettings:
        allResourceURIsList = getResourceURIs(driver, scrollPage=scrollPage, switchFrame=True, replaySystem=replaySystem, switchFrameAfterScroll=True, delayAfterScroll=livestreamSettings["delay_after_scroll"], recursive=True, framePathList=framePathList)
    else:
        allResourceURIsList = getResourceURIs(driver, scrollPage=scrollPage, switchFrame=True, replaySystem=replaySystem, switchFrameAfterScroll=True, recursive=True, framePathList=framePathList)
    
    # Remove duplicates from allResourceURIsList
    ## Removing duplicates from list: https://www.geeksforgeeks.org/python-ways-to-remove-duplicates-from-list/
    ### The order of the elements will change
    allResourceURIsList = [*set(allResourceURIsList)]
    
    scrollFrames = scrollPage
    
    uriRList = []
    removeURLList = []
    for url in allResourceURIsList:
        initialURL = url
        if replaySystem.lower() == "replayweb.page":
            if "about:blank" in url:
                url = "exclude"
            
            if "/replay/" in url:
                if len(url.split("http")) > 2:
                    url = "http" + "http".join(url.split("http")[2:])
                else:
                    url = "exclude" # Occurs for files used by the replay system like wombat.js
            
            if url != "exclude":
                uriRList.append(url)
            else:
                urlIndex = allResourceURIsList.index(initialURL)
                removeURLList.append(initialURL)

    # Remove the URIs that are used by the replay system, but are not from the live webpage
    for url in removeURLList:
        allResourceURIsList.remove(url)

    #'''
    #The capturedURIList should only contain URLs that we know are archived (except for soft 404s)
    #The missingResourceURIRList will contain the resources that are 404
    #Another category could be added for resources that may be archived 300 level status code
    #Could also have a category for other 400 or 500 errors
    capturedURIList = []
    missingResourceURIRList = []
    if os.path.exists(warcFilePath):
        with open(warcFilePath, 'rb') as stream:
            for record in ArchiveIterator(stream):
                if record.rec_type == "response":
                    targetURI = record.rec_headers.get_header('WARC-Target-URI')
                    if targetURI in uriRList and int(record.http_headers.get_statuscode()) == 200: #< 400:
                        index = uriRList.index(targetURI)
                        if not(uriRList[index] in capturedURIList):
                            capturedURIList.append(uriRList[index])
                    elif targetURI in uriRList and int(record.http_headers.get_statuscode()) == 404:
                        index = uriRList.index(targetURI)
                        if not(uriRList[index] in missingResourceURIRList):
                            missingResourceURIRList.append(uriRList[index])
    #'''
    
    '''
    if allCapturedURIsList == None:
        allCapturedURIsList = []
        with open(warcFilePath, 'rb') as stream:
            for record in ArchiveIterator(stream):
                if record.rec_type == "response":
                    targetURI = record.rec_headers.get_header('WARC-Target-URI')
                    if int(record.http_headers.get_statuscode()) < 400:
                        if not(targetURI in allCapturedURIsList):
                            allCapturedURIsList.append(targetURI)
    #'''
    
    '''Old approach
    missingResourceURIRList = []
    for uri in allResourceURIsList:
        if not(uri in capturedURIList):
            uriIndex = allResourceURIsList.index(uri)
            uriR = uriRList[uriIndex]
            if not(uriR in missingResourceURIRList):
                missingResourceURIRList.append(uriR)
                #print("\nURI from JavaScript: " + allResourceURIsList[uriIndex] + "\nURI-R not successfuly captured: " + uriR + "\n")
    #'''
    
    # Issue is occuring here, it seems like it keeps looping the annotation function for the same frame
    if annotateElements:
        annotateMissingResources(driver, replaySystem, allCapturedURIsList)

    #otherMissingResourcesURIRList = []
    ## scrollFrames should be false, because if scrollPage is true, then the scrollElementToBottom function should have already scrolled the frames
    #otherMissingResourcesURIRList = getMissingResourcesListFromFramesAndShadowDOMs(driver, livestreamSettings, replaySystem, warcFilePath, scrollFrames=False, annotateElements=annotateElements, allCapturedURIsList=allCapturedURIsList, maxDepth=(maxDepth-1))
    
    #missingResourceURIRList = [*set(missingResourceURIRList)] # remove duplicates (ordering of elements will change)
    #print("Missing Resource List Before Frames: " + str(len(missingResourceURIRList)))
            
    #missingResourceURIRList.extend(otherMissingResourcesURIRList)
    
    #missingResourceURIRList = [*set(missingResourceURIRList)] # remove duplicates (ordering of elements will change)
    #print("Missing Resource List After Frames: " + str(len(missingResourceURIRList)))
    
    return missingResourceURIRList, capturedURIList


def getBrozzlerEnvVars(brozzlerDriver, livestreamSettings):
    # Set the environment variable that will be used for Brozzler
    # Values that may be skipped '--skip-extract-outlinks', '--skip-visit-hashtags',
    windowX = brozzlerDriver.get_window_position()["x"]
    windowY = brozzlerDriver.get_window_position()["y"]
    windowWidth = brozzlerDriver.get_window_size()["width"]
    windowHeight = brozzlerDriver.get_window_size()["height"]
    if "user_data_dir" in livestreamSettings:
        userDataDir = livestreamSettings["user_data_dir"]
    else:
        userDataDir = os.path.abspath(os.getcwd())
    brozzlerEnvVars = os.environ.copy()
    brozzlerEnvVars["BROZZLER_EXTRA_CHROME_ARGS"] = """--disable-web-security --ignore-certificate-errors --window-position=%s,%s  --window-size=%s,%s"""%(windowX, windowY, windowWidth, windowHeight)
    #brozzlerEnvVars["BROZZLER_EXTRA_CHROME_ARGS"] = """--disable-web-security --ignore-certificate-errors --window-position=%s,%s  --window-size=%s,%s --user-data-dir="%s" """%(windowX, windowY, windowWidth, windowHeight, userDataDir)
    return brozzlerEnvVars



def getDefaultCollectionName(crawlerName="", uriIndex=-1):
    dateTimeFormat = "%Y_%m_%d_%H_%M_%S"
    warcDate = datetime.datetime.utcnow().strftime(dateTimeFormat)
    if crawlerName != "":
        crawlerName = crawlerName.replace(" ", "_") + "_"
    
    if uriIndex == -1:
        defaultCollectionName = crawlerName + 'collection_' + warcDate
    else:
        defaultCollectionName = crawlerName + 'collection_' + warcDate + "_seed_URI_" + str(uriIndex + 1)
        
    return defaultCollectionName

'''
def createBlankPage(title):
    blankPageCode="""<html><head><title>%s</title></head><body style="overflow: hidden;"></body></html>"""%(title)
    blankPageFile = open("blankPage.html", "w")
    blankPageFile.write(blankPageCode)
    blankPageFile.close()
'''


 
def getCrawlLogFilePathDict(crawlerList, crawlLogDirPathDict):
    crawlLogFilePathDict = {}
    
    for crawler in crawlerList:
        crawlLogFilePathDict[crawler] = []
    
    for currentCrawler in crawlerList:
        if currentCrawler in crawlLogDirPathDict:
            crawlLogDirPathList = crawlLogDirPathDict[currentCrawler]
            for currentDir in range(len(crawlLogDirPathList)):
                for filePath in os.listdir(currentDir):
                    if currentCrawler.lower() == "brozzler" and filePath.lower().endswith(".log"):
                        crawlLogFilePathDict.append(os.path.abspath(filePath))
                        
    return crawlLogFilePathDict

'''
def getMissingArchivedResourcesFromCDXJ(crawlerNameList, warcFilePathDict, livestreamSettings, startingTimestamp=None):

    if "use_previous_warc_records" in livestreamSettings and livestreamSettings["use_previous_warc_records"] == True:
        startingTimestamp = None # Making the starting timestamp none allows all records to be considered for this function

    missingArchivedResourcesDict = {}
    cdxjFilePath = os.path.abspath(os.getcwd()) + "/" + "temp.cdxj"
    
    # CDXJ for all WARCs approach
    for crawlerName in crawlerNameList:
        missingArchivedResourcesDict[crawlerName] = []
        if crawlerName in warcFilePathDict:
            warcFilePathList = warcFilePathDict[crawlerName]
            for index in range(len(warcFilePathList)):
                currentFilePath = warcFilePathList[index]
                subprocess.run("""cdxj-indexer "%s" >  %s"""%(currentFilePath, cdxjFilePath), shell=True)
                currentFile = open(cdxjFilePath, 'r')
                for line in currentFile:
                    jsonStr = "{\"" + line.split("{\"")[-1]
                    resourceDict = json.loads(jsonStr)
                    missingResourceUrl = resourceDict["url"]
                    timestamp = line.split("{\"")[-2].rstrip().split(" ")[-1]
                    if "status" in resourceDict:
                        statusCode = resourceDict["status"]
                    else:
                        statusCode = -1
                    if "mime" in resourceDict:
                        mimeType = resourceDict["mime"]
                    else:
                        mimeType = "unknown"
                    
                    if 400 <= int(statusCode) and int(statusCode) < 600:
                        ## Check if this resource should be considered based on the starting timestamp
                        cdxjDatetimeFormat = "%Y%m%d%H%M%S"
                        resourceDatetime = datetime.datetime.strptime(timestamp, cdxjDatetimeFormat)
                        if startingTimestamp == None or startingTimestamp < resourceDatetime:
                            missingArchivedResourcesDict[crawlerName].append(MissingResource(missingResourceUrl=missingResourceUrl, statusCode=statusCode, timestamp=timestamp, mimeType=mimeType))
                currentFile.close()
    return missingArchivedResourcesDict
'''

def getResourcesFromCDXJ(crawlerNameList, warcFilePathDict, livestreamSettings, startingTimestamp=None):
    
    if "use_previous_warc_records" in livestreamSettings and livestreamSettings["use_previous_warc_records"] == True:
        startingTimestamp = None # Making the starting timestamp none allows all records to be considered for this function

    allResourcesDict = {}
    cdxjFilePath = os.path.abspath(os.getcwd()) + "/" + "temp.cdxj"
    
    # CDXJ for all WARCs approach
    for crawlerName in crawlerNameList:
        allResourcesDict[crawlerName] = []
        if crawlerName in warcFilePathDict:
            warcFilePathList = warcFilePathDict[crawlerName]
            for index in range(len(warcFilePathList)):
                currentFilePath = warcFilePathList[index]
                if not os.path.exists(os.path.abspath(currentFilePath)):
                    continue
                
                subprocess.run("""cdxj-indexer "%s" >  %s"""%(currentFilePath, cdxjFilePath), shell=True)
                #subprocess.run(["""cdxj-indexer""", '''"%s"'''%(currentFilePath), ">",  '''"%s"'''%(cdxjFilePath)], shell=False)
                currentFile = open(cdxjFilePath, 'r')
                for line in currentFile:
                    jsonStr = "{\"" + line.split("{\"")[-1]
                    resourceDict = json.loads(jsonStr)
                    resourceUrl = resourceDict["url"]
                    timestamp = line.split("{\"")[-2].rstrip().split(" ")[-1]
                    if "status" in resourceDict:
                        statusCode = resourceDict["status"]
                    else:
                        statusCode = -1
                    if "mime" in resourceDict:
                        mimeType = resourceDict["mime"]
                    else:
                        mimeType = "unknown"
                    
                    ## Check if this resource should be considered based on the starting timestamp
                    cdxjDatetimeFormat = "%Y%m%d%H%M%S"
                    resourceDatetime = datetime.datetime.strptime(timestamp, cdxjDatetimeFormat)
                    if startingTimestamp == None or startingTimestamp < resourceDatetime:
                        allResourcesDict[crawlerName].append(Resource(resourceUrl=resourceUrl, statusCode=statusCode, timestamp=timestamp, mimeType=mimeType))
                
                currentFile.close()
    return allResourcesDict




 

    

    

def updateLiveWebPageInfo(webPageDriver, currentURL):
    #Info title
    try:
        webPageDriver.find_element(By.ID, "info_title")
    except NoSuchElementException:
        createInfoTitleScript="""
        var body = document.getElementsByTagName("body")[0];
        var name = document.createElement("h1");
        name.innerHTML = "%s";
        name.style.textAlign = "center";
        name.id = "info_title";
        body.appendChild(name);
        """%("Live Web Page")
        
        webPageDriver.execute_script(createInfoTitleScript)
    
    # URL line
    driverWidth = webPageDriver.get_window_size()["width"]
    createUrlLineScript ="""
    var currentUrlSpan = document.createElement("span");
    currentUrlSpan.style.fontSize = '2.09vw';
    currentUrlSpan.style.whiteSpace = 'nowrap';
    currentUrlSpan.style.width = '%spx';
    currentUrlSpan.style.overflow = 'hidden';
    currentUrlSpan.style.textOverflow = 'ellipsis';
    currentUrlSpan.style.display = 'inline-block';
    currentUrlSpan.style.margin = 'auto';
    currentUrlSpan.style.verticalAlign = 'middle';
    currentUrlSpan.style.lineHeight = '2.09vw';
    currentUrlSpan.innerHTML = '<b>Current URL</b>: %s';
    
    urlLine.appendChild(currentUrlSpan);
    """%(int(driverWidth * 1), currentUrl) #0.4 for two windows
        
    try:
        urlLine = crawlerInfoDriver.find_element(By.ID, "url_line")
        prevInnerHTML = urlLine.get_attribute("innerHTML")
        updateInfoScript= """var urlLine = document.createElement("p");""" + createUrlLineScript + """
        document.getElementById("url_line").innerHTML = urlLine.innerHTML;
        """
        webPageDriver.execute_script(updateInfoScript)
    except NoSuchElementException:
        createUrlLineScript="""
        var body = document.getElementsByTagName("body")[0];
        var urlLine = document.createElement("p");
        urlLine.style.textAlign = "center";
        urlLine.style.whiteSpace = 'nowrap';
        urlLine.id = "url_line";
        urlLine.style.width = '%spx';
        body.appendChild(urlLine);
        """%(driverWidth) + createUrlLineScript
        
        webPageDriver.execute_script(createUrlLineScript)

def updateCrawlerInfo(crawlerInfoDriver, currentStage, isLive=False, crawlerName="", currentUrl="", nextUrl="invalid", progress=""):
    #Crawler name
    try:
        crawlerInfoDriver.find_element(By.ID, "crawler_name")
        if crawlerName != "":
            updateInfoScript="""
            document.getElementById("crawler_name").innerHTML = "%s"
            """%(crawlerName)
            crawlerInfoDriver.execute_script(updateInfoScript)
    except NoSuchElementException:
        createCrawlerNameScript="""
        var body = document.getElementsByTagName("body")[0];
        var name = document.createElement("h1");
        name.innerHTML = "%s";
        name.style.textAlign = "center";
        name.id = "crawler_name";
        body.appendChild(name);
        """%(crawlerName)
        
        crawlerInfoDriver.execute_script(createCrawlerNameScript)
    
    # URL line
    driverWidth = crawlerInfoDriver.get_window_size()["width"]
    createUrlLineScript ="""
    var currentUrlSpan = document.createElement("span");
    currentUrlSpan.style.fontSize = "large";//'2.09vw';
    currentUrlSpan.style.whiteSpace = 'nowrap';
    currentUrlSpan.style.width = '%spx';
    currentUrlSpan.style.overflow = 'hidden';
    currentUrlSpan.style.textOverflow = 'ellipsis';
    currentUrlSpan.style.display = 'inline-block';
    currentUrlSpan.style.margin = 'auto';
    currentUrlSpan.style.verticalAlign = 'middle';
    currentUrlSpan.style.lineHeight = "large";//'2.09vw';
    currentUrlSpan.innerHTML = '<b>Current URL</b>: %s';
    
    urlLine.appendChild(currentUrlSpan);
    """%(int(driverWidth * 1), currentUrl) #0.4 for two windows
    
    if nextUrl != "invalid":
        createUrlLineScript = createUrlLineScript + """var nextUrlSpan = currentUrlSpan.cloneNode(true); nextUrlSpan.innerHTML = '<b>Next URL</b>: %s'; urlLine.appendChild(nextUrlSpan);"""%(nextUrl)
        
    try:
        urlLine = crawlerInfoDriver.find_element(By.ID, "url_line")
        prevInnerHTML = urlLine.get_attribute("innerHTML")
        updateInfoScript= """var urlLine = document.createElement("p");""" + createUrlLineScript + """
        document.getElementById("url_line").innerHTML = urlLine.innerHTML;
        """
        crawlerInfoDriver.execute_script(updateInfoScript)
    except NoSuchElementException:
        createUrlLineScript="""
        var body = document.getElementsByTagName("body")[0];
        var urlLine = document.createElement("p");
        urlLine.style.textAlign = "center";
        urlLine.style.whiteSpace = 'nowrap';
        urlLine.id = "url_line";
        urlLine.style.width = '%spx';
        body.appendChild(urlLine);
        """%(driverWidth) + createUrlLineScript
        
        crawlerInfoDriver.execute_script(createUrlLineScript)

    # Progress
    ## Determine the type of progress
    if isLive:
        progressType = "Viewed"
    elif currentStage.lower() == "archive":
        progressType = "Archived"
    elif currentStage.lower() == "replay":
        progressType = "Replayed"
    ## Update the progress
    try:
        crawlerInfoDriver.find_element(By.ID, "progress_text")
        if progress != "":
            updateInfoScript="""
            document.getElementById("progress_text").innerHTML = "<b>%s</b>: %s"
            """%(progressType, progress)
            crawlerInfoDriver.execute_script(updateInfoScript)
    except NoSuchElementException:
        createProgressScript="""
        var body = document.getElementsByTagName("body")[0];
        var progressText = document.createElement("p");
        progressText.innerHTML = "<b>%s</b>: %s";
        progressText.style.width = '%spx';
        progressText.style.margin = "auto";
        progressText.style.textAlign = "center";
        progressText.style.fontSize = "large";//"2vw";
        progressText.style.lineHeight = "2vw";
        progressText.id = "progress_text";
        body.appendChild(progressText);
        """%(progressType, progress, driverWidth)
        
        crawlerInfoDriver.execute_script(createProgressScript)

def updateStageInfo(stageInfoDriver, currentStage="", musicInfo=None, headingText="", hasArchiveStage=True, hasReplayStage=False, hasGameplayStage=False, hasResultsStage=False, updateList=None):
    
    if updateList == None:
        updateList = ["all"]
    
    #Current Stage
    if headingText == "":
        headingText = currentStage
    
    if ("all" in updateList or "heading" in updateList):
        try:
            stageInfoDriver.find_element(By.ID, "stage_name")
            if currentStage != "":
                updateInfoScript="""
                document.getElementById("stage_name").innerHTML = "%s"
                """%(headingText)
                stageInfoDriver.execute_script(updateInfoScript)
        except NoSuchElementException:
            createStageNameScript="""
            var body = document.getElementsByTagName("body")[0];
            var name = document.createElement("h1");
            name.innerHTML = "%s";
            name.style.textAlign = "center";
            name.style.margin = "4px";
            name.id = "stage_name";
            body.appendChild(name);
            """%(headingText)
            stageInfoDriver.execute_script(createStageNameScript)
    
    # Add Current Music Track Info
    if "all" in updateList or "music" in updateList:
        try:
            stageInfoDriver.find_element(By.ID, "music_info")
            if musicInfo != None:
                updateInfoScript="""
                document.getElementById("music_info").innerHTML = "Music: " + "%s";
                """%(musicInfo.title + " / by " + musicInfo.artist)
                stageInfoDriver.execute_script(updateInfoScript)
        except NoSuchElementException:
            createMusicInfoScript="""
            var musicInfo = document.createElement("p");
            musicInfo.innerHTML = "Music: " + "%s";
            musicInfo.style.textAlign = "center";
            musicInfo.style.fontSize = "1.3vw";
            musicInfo.style.margin = "4px";
            musicInfo.id = "music_info";
            
            stageList = document.getElementById("stage_list");
            if(stageList != null)
                document.body.insertBefore(musicInfo, stageList)
            else
                document.body.appendChild(musicInfo);
            """%(musicInfo.title + " / by " + musicInfo.artist)
            stageInfoDriver.execute_script(createMusicInfoScript)
    
    
    # Stage List
    if "all" in updateList or "stage list" in updateList:
        ## Create the code for the stage list
        currentStageCodeBeg = """<span style="background-color: lightgreen;">"""
        currentStageCodeEnd = """</span>"""
        
        stageListCode = ""
        if hasArchiveStage:
            if currentStage.lower() == "archive":
                stageListCode = currentStageCodeBeg + """Archive""" + currentStageCodeEnd
            else:
                stageListCode = """Archive"""
        if hasReplayStage:
            if currentStage.lower() == "replay":
                stageListCode = stageListCode + " | " + currentStageCodeBeg + """Replay""" + currentStageCodeEnd
            else:
                stageListCode = stageListCode + """ | Replay"""
        if hasGameplayStage:
            if currentStage.lower() == "gameplay":
                stageListCode = stageListCode + " | " + currentStageCodeBeg + """Gameplay""" + currentStageCodeEnd
            else:
                stageListCode = stageListCode + """ | Gameplay"""
        if hasResultsStage:
            if currentStage.lower() == "results":
                stageListCode = stageListCode + " | " + currentStageCodeBeg + """Results""" + currentStageCodeEnd
            else:
                stageListCode = stageListCode + """ | Results"""
        
        ## Update stage list
        try:
            stageInfoDriver.find_element(By.ID, "stage_list")
            if stageListCode != "":
                updateInfoScript="""
                document.getElementById("stage_list").innerHTML = '%s'
                """%(stageListCode)
                stageInfoDriver.execute_script(updateInfoScript)
        except NoSuchElementException:
            createListScript="""
            var body = document.getElementsByTagName("body")[0];
            var stageList = document.createElement("p");
            stageList.innerHTML = '%s';
            stageList.style.textAlign = "center";
            stageList.style.fontSize = "1.4vw";
            stageList.style.margin = "4px";
            stageList.id = "stage_list";
            body.appendChild(stageList);
            """%(stageListCode)
            stageInfoDriver.execute_script(createListScript)



def isMusicPlaying(driver):
    try:
        # If the music player does exists, then an error will not be thrown
        driver.find_element(By.ID, "music-audio-player")
        return True
    except:
        # If it does not exists an error will be thrown
        return False

def removeMusicPlayer(driver):
    if isMusicPlaying(driver):
        driver.execute_script("""
        var musicPlayer = document.getElementById("music-audio-player");
        musicPlayer.pause(); //If I do not pause, then an exception may be thrown which would stop future tracks from playing
        musicPlayer.remove();
        """)

def changeMusic(musicDF, driver, currentGenre, removeDuplicateMusicList, prevMusicIndexList=None, localServerPortNum=8090, delayBetweenTracks=2, numTracksBeforeRepeat=10):
    
    # Stop other track and play the next track
    if isMusicPlaying:
        removeMusicPlayer(stageInfoDriver)
    
    musicInfo = None
    currentMusicPath = None
    
    # Keep selecting random tracks until a track with the correct genere is selected
    ## Set prevMusicIndexList to an empty list if it does not exist
    if prevMusicIndexList is None:
        prevMusicIndexList = []
    ## Update numTracksBeforeRepeat if too large
    if numTracksBeforeRepeat >= len(musicDF["Music Title"]):
        numTracksBeforeRepeat = len(musicDF["Music Title"])
    ## Remove extra tracks from prevMusicIndexList
    while len(prevMusicIndexList) >= len(musicDF["Music Title"]) or len(prevMusicIndexList) >= numTracksBeforeRepeat:
        prevMusicIndexList.pop(0)
    randomMusicIndex = -1
    currentMusicGenre = ""
    numAttempts = 0
    while (randomMusicIndex == -1) or (randomMusicIndex in prevMusicIndexList) or (currentGenre.lower() == "all" and currentMusicGenre == "") or (currentGenre.lower() != "all" and currentMusicGenre.lower() != currentGenre.lower()):
        
        randomMusicIndex = randrange(0, len(musicDF["Music Title"]))
        numAttempts = numAttempts + 1
        
        ### Check if the audio file exists
        musicInfo = MusicTrackInfo(musicDF, randomMusicIndex)
        currentMusicFileName = musicDF["File Name"][randomMusicIndex]
        currentMusicPath = os.path.abspath(musicInfo.path)
        if not os.path.exists(currentMusicPath):
            randomMusicIndex = -1 # When the audio file cannot be used
            print('Error: The audio file "' + currentMusicPath + '" does not exist')
            continue
        else:
            ### Update music genre
            currentMusicGenre = musicDF["Genre"][randomMusicIndex]
        
        # Check if the number of attemps is too large which may occur when some of the music tracks cannot be played since they are non-existing files
        if numAttempts > len(musicDF["Music Title"]):
            ## Clear the list of previously played music
            prevMusicIndexList.clear()
    
    prevMusicIndexList.append(randomMusicIndex)
    updateStageInfo(stageInfoDriver, musicInfo=musicInfo, updateList=["music"])
    
    cwd = os.getcwd()
    try: #Try to copy the music to the current directory
        shutil.copy2(currentMusicPath, cwd)
    except:
        ""#print("music already exists")
    
    if (cwd + currentMusicFileName) not in removeDuplicateMusicList:
        removeDuplicateMusicList.append(cwd + "/" + currentMusicFileName)

    #'''
    # Create the music URL
    musicStartTime = 0
    if not pd.isna(musicDF["Start Time"][randomMusicIndex]):
        musicStartTime = int(musicDF["Start Time"][randomMusicIndex])
    
    musicStopTime = -1
    if not pd.isna(musicDF["Stop Time"][randomMusicIndex]):
        musicStopTime = int(musicDF["Stop Time"][randomMusicIndex])
    else:
        with audioread.audio_open(currentMusicPath) as musicFile:
            # Set music stop time to the duration of the music
            ## Reduce the duration by a fraction of a second, because the stop time should be before the end of the track
            musicStopTime = int(math.floor(musicFile.duration))
    
    musicDuration = musicStopTime - musicStartTime
    
    # This does not consistently work so it was removed
    musicFragmentStr = """#t=%s,%s"""%(musicStartTime, musicStopTime)
    print(musicFragmentStr)
    
    #musicURL = "http://127.0.0.1:" + str(localServerPortNum) + "/" + currentMusicFileName + musicFragmentStr
    musicURL = "http://127.0.0.1:" + str(localServerPortNum) + "/" + currentMusicFileName
    musicURL = musicURL.replace(" ", "%20")
    musicURL = musicURL.replace("\t", "%20")
    
    playMusicScript ="""
    ///Audio
    /*
    <video controls="" autoplay="" name="media"><source src="musicURL"></video>
    */
    function createMusicPlayer(musicURL)
    {
        
        var musicAudioPlayer = document.createElement("audio");
        musicAudioPlayer.id = "music-audio-player";
        musicAudioPlayer.setAttribute('name', 'media');

        var musicAudioSrc = document.createElement("source");
        musicAudioSrc.setAttribute("src", musicURL);
        musicAudioSrc.setAttribute("type", "audio/mpeg");
        musicAudioPlayer.appendChild(musicAudioSrc);
        document.body.appendChild(musicAudioPlayer);
        
        return musicAudioPlayer;
    }
    
    const delay = ms => new Promise(res => setTimeout(res, ms));
    const playMusic = async(musicAudioPlayer, delayBetweenTracks, musicFragment) => {
        await delay(delayBetweenTracks);
        musicAudioPlayer.children[0].setAttribute("src", musicURL + musicFragment);
        console.log(musicAudioPlayer.children[0].getAttribute("src"))
        musicAudioPlayer.play();
    }
    
    const removeMusicPlayer = async (musicAudioPlayer, musicDuration) => {
        await delay(musicDuration * 1000);
        if(Array.from(document.body.children).includes(musicAudioPlayer))
            musicAudioPlayer.remove();
    }
    var musicStartTime = %s;
    var musicURL = "%s";
    var musicFragment = "%s";
    var musicDuration = %s;
    var delayBetweenTracks = %s;
    musicAudioPlayer = createMusicPlayer(musicURL)
    playMusic(musicAudioPlayer, delayBetweenTracks, musicFragment)
    removeMusicPlayer(musicAudioPlayer, musicDuration + delayBetweenTracks);
    """%(musicStartTime, musicURL, musicFragmentStr, musicDuration, delayBetweenTracks)
    driver.find_elements(By.TAG_NAME, "body")[0].click(); #Need to interact with the driver before playing audio
    driver.execute_script(playMusicScript)
    
    return musicInfo, musicDuration

def startWarcprox(crawlerName, livestreamSettings, defaultValuesDict, warcFilePathDict, crawlLogDirPathDict,  brozzlerDriver=None, screenWidth=-1, screenHeight=-1, dedupFilePath="", uriIndex=-1):
    if screenWidth <= 0 or screenHeight <= 0:
        screenWidth,screenHeight = getWindowDimensions()
    
    # Run warcprox
    ## Get the values for the warcprox command
    if brozzlerDriver != None:
        brozzlerEnvVars = getBrozzlerEnvVars(brozzlerDriver, livestreamSettings)
    else:
        brozzlerEnvVars = os.environ.copy()
    if "warcprox_python_virtual_environment_path" in livestreamSettings:
        pythonPath = livestreamSettings["warcprox_python_virtual_environment_path"]
    else:
        pythonPath = defaultValuesDict["python_version"]
    
    if "warcprox_port_number" in livestreamSettings:
        warcproxPortNum = livestreamSettings["warcprox_port_number"]
    else:
        warcproxPortNum = defaultValuesDict["warcprox_port_number"]
    
    if "warcprox_output_directory" in livestreamSettings:
        warcproxOutputDir = livestreamSettings["warcprox_output_directory"]
    else:
        warcproxOutputDir = os.path.abspath(os.getcwd()) + "/" + crawlerName + "_warcs/" + getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    if "warcprox_crawl_log_directory" in livestreamSettings:
        crawlLogDir = livestreamSettings["warcprox_crawl_log_directory"]
    else:
        crawlLogDir = warcproxOutputDir
    
    if not os.path.exists(warcproxOutputDir):
        Path(warcproxOutputDir).mkdir(parents=True, exist_ok=True)
    
    if "warcprox_output_file_name" in livestreamSettings:
        warcFileName = livestreamSettings["warcprox_output_file_name"]
    else:
        warcFileName = getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    if dedupFilePath == "":
        if "warcprox_deduplication_file_path" in livestreamSettings:
            dedupFilePath = livestreamSettings["warcprox_deduplication_file_path"]
        else:
            dedupFilePath = defaultValuesDict["warcprox_deduplication_file_path"]
    
    # Creating the dedup file
    dedupFile = open(dedupFilePath, "w")
    dedupFile.close()
    ## Copy the dedup file to the output directory
    shutil.copy2(dedupFilePath, warcproxOutputDir)
    
    ## Run the warcprox command
    warcproxProcess = subprocess.Popen(['warcprox', '-p', warcproxPortNum, '-d', warcproxOutputDir, '--crawl-log-dir', crawlLogDir, '--warc-filename', warcFileName, '--dedup-db-file', dedupFilePath, '--gzip'], env=brozzlerEnvVars, shell=False, stderr=subprocess.PIPE) # currently does not work
    #warcproxProcess = subprocess.Popen([pythonPath, '-m','warcprox', '-p', warcproxPortNum, '-d', warcproxOutputDir, '--dedup-db-file', dedupFilePath, '--gzip', '-q'], env=brozzlerEnvVars, stderr=subprocess.PIPE) # currently does not work
    
    if crawlerName not in warcFilePathDict:
        warcFilePathDict[crawlerName] = []
    if crawlerName not in crawlLogDirPathDict:
        crawlLogDirPathDict[crawlerName] = []
    
    warcFilePath = os.path.abspath(warcproxOutputDir) + "/" + warcFileName + ".warc.gz"
    warcFilePathDict[crawlerName].append(warcFilePath)
    
    if crawlLogDir not in crawlLogDirPathDict[crawlerName]:
        crawlLogDirPathDict[crawlerName].append(warcFilePath)
    
    return warcproxProcess


def restartWarcprox(oldWarcproxProcess, crawlerName, livestreamSettings, defaultValuesDict, warcFilePathDict, crawlLogDirPathDict, brozzlePageProcess, brozzlerDriver=None, screenWidth=-1, screenHeight=-1, dedupFilePath="", uriIndex=-1):
    # Terminate old process
    terminateProcess(oldWarcproxProcess)
    
    #Kill the brozzle page process
    killProcess(brozzlePageProcess)
    
    # Get new process
    newWarcproxProcess = startWarcprox(crawlerName, livestreamSettings, defaultValuesDict, warcFilePathDict, crawlLogDirPathDict, brozzlerDriver=brozzlerDriver, screenWidth=screenWidth, screenHeight=screenHeight, dedupFilePath=dedupFilePath, uriIndex=uriIndex)
    
    return newWarcproxProcess

# brozzlerEnvVars should have --ignore-certificate-errors included so that brozzle-page will work
def brozzlePage(url, brozzlerDriver, livestreamSettings, defaultValuesDict):
    crawlerName = "brozzler"
    
    # Get the values for the brozzle-page command
    brozzlerEnvVars = getBrozzlerEnvVars(brozzlerDriver, livestreamSettings)
    ## Example Chrome paths:
    ### MacOS: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
    ### Linux: /usr/bin/google-chrome
    ### Windows: C:\Program Files (x86)\Google\Chrome\Application
    if "chrome_executable_path" in livestreamSettings:
        chromePath = livestreamSettings["chrome_executable_path"]
    else:
        print("Error in brozzlePage(): The livestream settings file needs to have a value for \"chrome_executable_path\" if Brozzler is used.")
        exit()
    
    if "warcprox_port_number" in livestreamSettings:
        proxy = "localhost:" + livestreamSettings["warcprox_port_number"]
    else:
        proxy = "localhost:" + defaultValuesDict["warcprox_port_number"]
    
    brozzlePageProcess = subprocess.Popen(['brozzle-page', '--chrome-exe', chromePath, '--proxy', proxy, url], env=brozzlerEnvVars, shell=False, stderr=subprocess.PIPE)
    
    return brozzlePageProcess

def checkBrozzlerView(brozzlerDriver, isArchivingNewURL=True, isFinished=False, finishedSet=False):
    title = "Brozzler"
    
    if finishedSet:
        text = "Brozzler Has Finished The Archiving Speedrun"
    elif isArchivingNewURL:
        # Diplay the waiting related webpage
        text = "Waiting For Brozzler To Open Browser Window"
    elif isFinished:
        text = "Brozzler Has Finished Archiving The Current URL"
    
    waitingPageCode="""<html><head><title>%s</title></head><body><h1>%s</h1></body></html>"""%(title, text)
    dataForDriver = "data:text/html," + waitingPageCode
    
    if isArchivingNewURL or isFinished:
        brozzlerDriver.get(dataForDriver)

def browsertrixCrawl(url, livestreamSettings, defaultValuesDict, warcFilePathDict, uriIndex=-1, crawlTimeLimit=300):
    crawlerName = "browsertrix"
    # Get the values for the browsertrix crawler command
    if "browsertrix_port_number" in livestreamSettings:
        portNum = livestreamSettings["browsertrix_port_number"]
    else:
        portNum = defaultValuesDict["browsertrix_port_number"]
    portNumbersOption = portNum + ":" + portNum
    screencastPortOption = "--screencastPort=" + portNum
    
    if "browsertrix_output_directory" in livestreamSettings:
        outputDir = livestreamSettings["browsertrix_output_directory"]
    else:
        outputDir = os.path.abspath(os.getcwd())
    outputDirOption = outputDir + ":" + "/crawls"
    
    if "browsertrix_output_file_option" in livestreamSettings:
        outputFileOption = livestreamSettings["browsertrix_output_file_option"]
    else:
        outputFileOption = defaultValuesDict["browsertrix_output_file_option"]
    
    if "browsertrix_collection_name" in livestreamSettings:
        collectionName = livestreamSettings["browsertrix_collection_name"]
    else:
        collectionName = getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    
    commandStr = """docker run -p %s -v %s -it webrecorder/browsertrix-crawler crawl --url %s %s --timeLimit %s --text --allowHashUrls --behaviors autoscroll,autoplay --limit 1  %s --collection %s"""%(portNumbersOption, outputDirOption, url, outputFileOption, str(crawlTimeLimit), screencastPortOption, collectionName)
    
    browsertrixProcess = subprocess.Popen(commandStr, shell=True)
    #browsertrixProcess = subprocess.Popen(['docker', 'run', '-p', portNumbersOption, '-v', outputDirOption, '-it', 'webrecorder/browsertrix-crawler', 'crawl', '--url', url, outputFileOption,'--timeLimit', str(crawlTimeLimit), '--text', '--allowHashUrls', '--behaviors', 'autoscroll,autoplay', '--limit', '1',  screencastPortOption, '--collection', collectionName], shell=False)
    
    
    if crawlerName not in warcFilePathDict:
        warcFilePathDict[crawlerName] = []
    
    warcFilePath = os.path.abspath(os.getcwd()) + "/" + "collections/" + collectionName + "/" + collectionName + "_0.warc.gz"
    warcFilePathDict[crawlerName].append(warcFilePath)
    
    return browsertrixProcess

def showBrowsertrixWaitingPage(browsertrixDriver, isFinished, title):
    # Diplay the waiting related webpage
    if isFinished:
        text = "Browsertrix Has Finished The Screencast"
    else:
        text = "Waiting For Browsertrix To Begin Screencasting The Crawl"

    waitingPageCode="""<html><head><title>%s</title></head><body><h1>%s</h1></body></html>"""%(title, text)
    dataForDriver = "data:text/html," + waitingPageCode

    browsertrixDriver.get(dataForDriver)

def checkBrowsertrixView(browsertrixDriver, livestreamSettings, defaultValuesDict, isArchivingNewURL=True, isFinished=False, finishedSet=False):
    title = "Browsertrix"
    if finishedSet:
        text = "Browsertrix Has Finished The Archiving Speedrun"
        
        waitingPageCode="""<html><head><title>%s</title></head><body><h1>%s</h1></body></html>"""%(title, text)
        dataForDriver = "data:text/html," + waitingPageCode
        
        if len(browsertrixDriver.find_elements(By.TAG_NAME, "h1")) != 1 or (len(browsertrixDriver.find_elements(By.TAG_NAME, "h1")) > 0 and browsertrixDriver.find_elements(By.TAG_NAME, "h1")[0].get_attribute("innerHTML") != text):
            
            browsertrixDriver.get(dataForDriver)
            
    elif isArchivingNewURL or len(browsertrixDriver.find_elements(By.TAG_NAME, "div")) != 1 or (len(browsertrixDriver.find_elements(By.TAG_NAME, "div")) > 0 and browsertrixDriver.find_elements(By.TAG_NAME, "div")[0].get_attribute("id") != "content") or len(browsertrixDriver.find_element(By.ID, "content").find_elements(By.TAG_NAME, "img")) != 1:
        
        #Attempt to load the browsetrix's screencast
        try:
            if "browsertrix_port_number" in livestreamSettings:
                portNum = livestreamSettings["browsertrix_port_number"]
            else:
                portNum = defaultValuesDict["browsertrix_port_number"]
            screencastWebPage = "http://127.0.0.1:" + portNum + "/"
        
            browsertrixDriver.get(screencastWebPage)
            
            if isArchivingNewURL or len(browsertrixDriver.find_elements(By.TAG_NAME, "div")) != 1 or (len(browsertrixDriver.find_elements(By.TAG_NAME, "div")) > 0 and browsertrixDriver.find_elements(By.TAG_NAME, "div")[0].get_attribute("id") != "content") or len(browsertrixDriver.find_element(By.ID, "content").find_elements(By.TAG_NAME, "img")) != 1:
                showBrowsertrixWaitingPage(browsertrixDriver, isFinished, title)
        except:
            showBrowsertrixWaitingPage(browsertrixDriver, isFinished, title)

def wgetCrawl(currentUrl, wgetDriver, livestreamSettings, defaultValuesDict, warcFilePathDict, crawlTimeLimit=300, uriIndex=-1):
    
    crawlerName = "wget"
    if "wget_output_directory" in livestreamSettings:
        wgetOutputDir = livestreamSettings["wget_output_directory"]
    else:
        wgetOutputDir = os.path.abspath(os.getcwd()) + "/" + crawlerName + "_warcs/" + getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    ''' # may add later
    if "wget_crawl_log_directory" in livestreamSettings:
        crawlLogDir = livestreamSettings["wget_crawl_log_directory"]
    else:
        crawlLogDir = wgetOutputDir
    #'''
    
    if not os.path.exists(wgetOutputDir):
        Path(wgetOutputDir).mkdir(parents=True, exist_ok=True)
    
    if "wget_output_file_name" in livestreamSettings:
        warcFileName = livestreamSettings["wget_output_file_name"].replace(" ", "\ ")
    else:
        warcFileName = getDefaultCollectionName(crawlerName, uriIndex=uriIndex).replace(" ", "\ ")
    
    if crawlerName not in warcFilePathDict:
        warcFilePathDict[crawlerName] = []
    ''' # may add later
    if crawlerName not in crawlLogDirPathDict:
        crawlLogDirPathDict[crawlerName] = []
    #'''
    
    warcFilePath = os.path.abspath(wgetOutputDir) + "/" + warcFileName + ".warc.gz"
    warcFilePathDict[crawlerName].append(warcFilePath)
    
    ''' # may add later
    if crawlLogDir not in crawlLogDirPathDict[crawlerName]:
        crawlLogDirPathDict[crawlerName].append(warcFilePath)
    #'''
    
    wgetCommand = """wget -pk --timeout=%s --warc-file=%s "%s" """%(crawlTimeLimit, warcFileName, currentUrl)
    
    updateWgetWindowCode = """
    var wgetCommand = document.getElementById("command");
    var beginLine = "> ";
    wgetCommand.innerHTML = beginLine.concat('%s');
    """%(wgetCommand)
    wgetDriver.execute_script(updateWgetWindowCode)
    wgetProcess = subprocess.Popen(['wget', '-pk', """--timeout=%s"""%(crawlTimeLimit), """--warc-file=%s"""%(warcFileName), currentUrl], shell=False, stderr=subprocess.PIPE)
    
    return wgetProcess
    

def moveWARCFileForWget(crawlerName, warcFilePathDict):
    filePath, fileExtension = os.path.splitext(warcFilePathDict[crawlerName][-1])
    if not os.path.exists(filePath):
        return #exit
    fileName = filePath.split("/")[-1] + fileExtension
    oldWarcFilePath = os.path.abspath(os.getcwd()) + "/" + fileName
    oldWarcFilePath = oldWarcFilePath.replace("//", "/") # Replace // if the cwd is at the root directory
    newWarcFilePath = warcFilePathDict[crawlerName][-1]
    
    if oldWarcFilePath != newWarcFilePath:
        shutil.copy2(oldWarcFilePath, newWarcFilePath)
        os.remove(oldWarcFilePath)

def scriptorCrawl(currentUrl, scriptorDriver, livestreamSettings, defaultValuesDict, warcFilePathDict, uriIndex=-1):
    crawlerName = "webis scriptor"
    if "webis_scriptor_output_directory" in livestreamSettings:
        outputDir = os.path.abspath(livestreamSettings["webis_scriptor_output_directory"])
    else:
        outputDir = os.path.abspath(os.getcwd()) + "/" + crawlerName.replace(" ", "_") + "_warcs/" + getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    scriptorLockedDir = outputDir + "/scriptor_output"
    
    if not os.path.exists(scriptorLockedDir):
        Path(scriptorLockedDir).mkdir(parents=True, exist_ok=True)
    
    if "webis_scriptor_output_file_name" in livestreamSettings:
        warcFileName = livestreamSettings["webis_scriptor_output_file_name"].replace(" ", "\ ")
    else:
        warcFileName = getDefaultCollectionName(crawlerName, uriIndex=uriIndex).replace(" ", "\ ")
    
    if crawlerName not in warcFilePathDict:
        warcFilePathDict[crawlerName] = []
    
    # Output directory for WARC file when using Webis Scriptor
    warcFileDir = scriptorLockedDir + "/" + "browserContexts/default/warcs/collections/scriptor/archive"
    
    warcFilePath = os.path.abspath(warcFileDir) + "/" + warcFileName + ".warc.gz"
    warcFilePathDict[crawlerName].append(warcFilePath)
    
    #Example command (docker)
    ## docker run -it --rm --volume /home/userName/Documents:/output ghcr.io/webis-de/scriptor:latest --input "{\"url\": \"https://artsandculture.google.com/story/mwURGp1URe8zgg\"}"
    command = '''docker run -it --rm --volume %s:/output ghcr.io/webis-de/scriptor:latest --input "{"url": "%s"}"'''%(scriptorLockedDir, currentUrl)
    #command = '''scriptor --input "{\"url\": \"%s\"}" --output-directory %s'''%(currentUrl, scriptorLockedDir)
    
    
    updateWindowCode = """
    var command = document.getElementById("command");
    var beginLine = "> ";
    command.innerHTML = beginLine.concat('%s');
    """%(command)
    scriptorDriver.execute_script(updateWindowCode)
    commandArguments = ['docker', 'run', '-it', '--rm', '-v', """%s:/output"""%(scriptorLockedDir), 'ghcr.io/webis-de/scriptor:latest', '--input', '{"url": "%s"}'%(currentUrl)]
    #commandArguments = ['scriptor', '--input', "{\"url\": \"%s\"}"%(currentUrl), '--output-directory', scriptorLockedDir]
    commandStr = """docker run -it --rm -v %s:/output ghcr.io/webis-de/scriptor:latest --input '{"url": "%s"}'"""%(scriptorLockedDir, currentUrl)
    #scriptorProcess = subprocess.Popen(" ".join(commandArguments), shell=True, stdout=subprocess.PIPE)
    scriptorProcess = subprocess.Popen(commandStr, shell=True, stdout=subprocess.PIPE)
    #scriptorProcess = subprocess.Popen(commandArguments, shell=False, stdout=subprocess.PIPE)
    
    
    return scriptorProcess

def renameWARCFileForScriptor(crawlerName, warcFilePathDict):
    oldWarcFilePath = warcFilePathDict[crawlerName][-1]
    warcFileName = warcFilePathDict[crawlerName][-1].split("/")[-1]
    
    # Get parent directory for the WARC file
    ## Need to get the absolute path before getting the parent directory
    ## warcFileDir will be a Path object so may need to use str(warcFileDir) in some cases
    warcFileDir = Path(oldWarcFilePath).absolute().parent

    if not os.path.exists(warcFileDir):
        return #exit
    
    # Get the current name of the WARC file (If there is more than one WARC file this will break. Need to check if it is possible to have multiple WARC files when the WARC file gets too large)
    ## If there are multiple WARCs, then the WARCs would need to be combined into one WARC file
    for currentFileName in warcFileDir.iterdir():
        if ".warc.gz" in str(currentFileName).lower():
            oldWarcFilePath = str(currentFileName.absolute())
            break

    if not os.path.exists(oldWarcFilePath):
        return #exit
        
    # A copy of the WARC file is made, because Webis Scriptor changes the permisssion to read only for the original WARC file which prevents the name of the original WARC file from being changed to the file name specified by the user
    newWarcFilePath = str(warcFileDir.parent.parent.parent.parent.parent.parent.parent) + "/" + warcFileName
    if oldWarcFilePath != newWarcFilePath:
        print("""cp %s %s"""%(oldWarcFilePath, newWarcFilePath))
        subprocess.run("""cp %s %s"""%(oldWarcFilePath, newWarcFilePath), shell=True)
        warcFilePathDict[crawlerName][-1] = newWarcFilePath

def squidwarcCrawl(currentUrl, squidwarcDriver, livestreamSettings, defaultValuesDict, warcFilePathDict, crawlTimeLimit=300, uriIndex=-1):
    crawlerName = "squidwarc"
    if "squidwarc_output_directory" in livestreamSettings:
        outputDir = livestreamSettings["squidwarc_output_directory"]
    else:
        outputDir = os.path.abspath(os.getcwd()) + "/" + crawlerName.replace(" ", "_") + "_warcs/" + getDefaultCollectionName(crawlerName, uriIndex=uriIndex)
    
    if not os.path.exists(outputDir):
        Path(outputDir).mkdir(parents=True, exist_ok=True)
    
    if "squidwarc_output_file_name" in livestreamSettings:
        warcFileName = livestreamSettings["squidwarc_output_file_name"].replace(" ", "\ ")
    else:
        warcFileName = getDefaultCollectionName(crawlerName, uriIndex=uriIndex).replace(" ", "\ ")
    
    if crawlerName not in warcFilePathDict:
        warcFilePathDict[crawlerName] = []
    
    warcFilePath = (os.path.abspath(outputDir) + "/" + warcFileName + ".warc").replace("//", "/")
    warcFilePathDict[crawlerName].append(warcFilePath)
    
    # Check if the livestream settings has Squidwarc's directory path
    if "squidwarc_directory_path" not in livestreamSettings:
        print('Need to set the "squidwarc_directory_path" option when using the Squidwarc crawler')
        exit()
    else:
        squidwarcDir = livestreamSettings["squidwarc_directory_path"]
    
    if "squidwarc_port_number" in livestreamSettings:
        portNum = livestreamSettings["squidwarc_port_number"]
    else:
        portNum = 9222 #Default used by Squidwarc
    
    # Create a temporary configuration file for Squidwarc
    configScript = """
    {
      "use": "puppeteer",
      "headless": %s,
      "script": "%s/userFns.js",
      "mode": "page-only",
      "depth": 1,
      "seeds": [
        "%s"
      ],
      "warc": {
        "naming": "%s",
        "output": "%s"
      },
      "connect": {
        "launch": true,
        "host": "localhost",
        "port": %s
      },
      "crawlControl": {
        "globalWait": %s,
        "inflightIdle": 1000,
        "numInflight": 2,
        "navWait": 8000
      }
    }
    """%(str(livestreamSettings["squidwarc_headless"]).lower(), squidwarcDir, currentUrl, warcFileName, os.path.abspath(outputDir), portNum, crawlTimeLimit * 1000)
    configFileName = "temp_squidwarc_conf.json"
    configFilePath = os.path.abspath(os.getcwd()) + "/" + configFileName
    configFile = open(configFileName, 'w')
    configFile.write(configScript)
    configFile.close()
    
    runCrawlerScript = (squidwarcDir + "/" + "run-crawler.sh").replace("//", "/")
    
    #command = """./run-crawler.sh -c %s"""%(configFileName)
    command = """node --harmony index.js -c %s"""%(configFileName)
    updateWindowCode = """
    var command = document.getElementById("command");
    var beginLine = "> ";
    command.innerHTML = beginLine.concat('%s');
    """%(command)
    squidwarcDriver.execute_script(updateWindowCode)
    #squidwarcProcess = subprocess.Popen([runCrawlerScript, '-c', configFilePath], cwd=squidwarcDir, stdout=subprocess.PIPE)
    #squidwarcProcess = subprocess.Popen(['node', '--harmony', 'index.js', '-c', configFilePath], cwd=squidwarcDir, stdout=subprocess.PIPE)
    #squidwarcProcess = subprocess.Popen(['node', '--harmony', "%s/index.js"%(squidwarcDir), '-c', configFilePath], stdout=subprocess.PIPE)
    squidwarcProcess = subprocess.Popen("node --harmony %s/index.js -c %s"%(squidwarcDir, configFilePath), shell=True, stdout=subprocess.PIPE)
    #squidwarcProcess = subprocess.Popen(["node", "--harmony", """%s/index.js"""%(squidwarcDir), "-c", '''"%s"'''%(configFilePath)], shell=False, stdout=subprocess.PIPE)
    
    return squidwarcProcess

def removeSquidwarcConfig():
    fileName = "temp_squidwarc_conf.json"
    if os.path.exists(fileName):
        os.remove(fileName)

def displayFinishedStatusForCommandWindow(commandDriver, crawlerName="", title="", finishedSet=False):
    if title == "" and crawlerName == "":
        title = "Command Window"
    elif crawlerName != "":
        crawlerName = crawlerName[0].upper() + crawlerName[1:]
        title = crawlerName
    
    if crawlerName != "":
        if finishedSet:
            text = crawlerName + " Has Finished The Archiving Speedrun"
        else:
            text = crawlerName + " Has Finished Archiving The Current URL"
    else:
        text = "The Previous Command Has Completed Execution"
    
    blankPageCode="""<html><head><title>%s</title></head><body></body></html>"""%(title)
    dataForDriver = "data:text/html," + blankPageCode
    
    if len(commandDriver.find_elements(By.TAG_NAME, "h1")) != 2 or commandDriver.find_elements(By.TAG_NAME, "h1")[0].get_attribute("innerHTML") != text:
        commandDriver.get(dataForDriver)
        
        updateWindowCodeScript = """
        document.body.style.backgroundColor = "black";
        var commandLine = document.createElement("h1");
        commandLine.id = "command";
        commandLine.style.color = "white";
        commandLine.innerHTML = "%s";
        document.body.appendChild(commandLine);

        var outputLine = document.createElement("h1");
        outputLine.id = "command_output";
        outputLine.style.color = "white";
        document.body.appendChild(outputLine);
        """%(text)
        commandDriver.execute_script(updateWindowCodeScript)


### Replay Functions ###
def embedReplayWebPage(windowDriver, warcFilePath, url, crawlerName, livestreamSettings, defaultValuesDict):
    replaySystem = "replayweb_page"
    htmlFileName = crawlerName + "_and_" + replaySystem + ".html"
    if crawlerName.lower() == "brozzler":
        newName, oldExtension = os.path.splitext(warcFilePath)
        if os.path.exists(warcFilePath):
            if oldExtension.replace(".", "") == "open":
                os.rename(warcFilePath, newName)
                warcFilePath = newName
        else:
            warcFilePath = newName

    if "replay_web_page_port_number" in livestreamSettings:
        portNum = livestreamSettings["replay_web_page_port_number"]
    else:
        portNum = defaultValuesDict["replay_web_page_port_number"]
    
    if "replay_web_page_version" in livestreamSettings:
        replayWebPageVersion = livestreamSettings["replay_web_page_version"]
    else:
        replayWebPageVersion = defaultValuesDict["replay_web_page_version"]
    
    # Move a copy of the warc file to the current directory
    try:
        copiedWarcFilePath = os.path.abspath(os.getcwd()) + "/" + os.path.basename(warcFilePath)
        if os.path.exists(copiedWarcFilePath):
            copiedWarcFilePath = None
        
        # Cannot use shutil.copy2 to copy webis scriptor's WARC file
        if crawlerName.lower() != "webis scriptor":
            relWarcFilePath = os.path.relpath(shutil.copy2(warcFilePath, os.path.abspath(os.getcwd())))
        else:
            filePath, fileExtension = os.path.splitext(warcFilePath)
            fileName = filePath.split("/")[-1] + fileExtension
            subprocess.run("""cp %s %s"""%(warcFilePath, os.path.abspath(os.getcwd()) + "/" + fileName), shell=True)
            relWarcFilePath = os.path.relpath(os.path.abspath(os.getcwd()) + "/" + fileName)
    except:
        title = "Missing WARC File"
        text = "The WARC File Does Not Exist For This Web Page"
        webPageCode="""<html><head><title>%s</title></head><body><h1>%s</h1></body></html>"""%(title, text)
        dataForDriver = "data:text/html," + webPageCode
        windowDriver.get(dataForDriver)
        return "" # Exit the function
    
    # Create the sw.js file needed to replay the web page
    deleteReplayFolder = True
    replayFolderPath = os.path.abspath(os.getcwd()) + "/" + "replay"
    if os.path.exists(replayFolderPath):
        deleteReplayFolder = False
    else:
        Path(replayFolderPath).mkdir(parents=True, exist_ok=True)
    swJSfile = open(replayFolderPath + "/" + "sw.js", 'w')
    swJSscript = """
    importScripts("https://cdn.jsdelivr.net/npm/replaywebpage@%s/sw.js");
    """%(replayWebPageVersion)
    swJSfile.write(swJSscript)
    swJSfile.close()
    
    
    if "replay_web_page_embed_type" in livestreamSettings:
        embedType = livestreamSettings[replay_web_page_embed_type]
    else:
        embedType = defaultValuesDict["replay_web_page_embed_type"]
    webPageCode = """<html><head><script src="https://cdn.jsdelivr.net/npm/replaywebpage@%s/ui.js"></script></head><body><replay-web-page source="%s" url="%s" embed="%s"></replay-web-page></body></html>"""%(replayWebPageVersion, relWarcFilePath, url, embedType)
    
    # Print the HTML file needed
    htmlFilePath = os.path.abspath(os.getcwd()) + "/" + htmlFileName
    htmlFile = open(htmlFilePath, 'w')
    htmlFile.write(webPageCode)
    htmlFile.close()
    
    webPage = "http://127.0.0.1:" + portNum + "/" + htmlFileName
    try:
        windowDriver.get(webPage)
    except:
        print("Error when loading webpage")
    
    ''' Need to delete the file
    # Delete the copied file
    if copiedWarcFilePath != None:
        os.remove(copiedWarcFilePath)
        
    # Delete the temporary replay folder
    if deleteReplayFolder:
        shutil.rmtree(replayFolderPath, ignore_errors=True)
    #'''
    

def replayWebPage(windowDriver, warcFilePath, url, crawlerName, replaySystem, livestreamSettings, defaultValuesDict):
    if replaySystem.lower() == "replayweb.page":
        embedReplayWebPage(windowDriver, warcFilePath, url, crawlerName, livestreamSettings, defaultValuesDict)

def scrollWebPage(webPageDriver, livestreamSettings, defaultValuesDict, loadDelay=-1, willPlayMusic=False, musicDriver=None, musicDF=None, musicInfo=None, localServerPortNum=None, currentMusicGenre="all", prevMusicIndexList=None, delayBetweenTracks=0):
    
    musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
    
    getScrollHeightScript = """return document.body.scrollHeight"""
    scrollDownScript = """window.scrollBy(0, 1)"""
    
    # Get the scroll heights for the current window
    currentScrollHeight = webPageDriver.execute_script(getScrollHeightScript)
    previousScrollHeight = 0
    
    # Scroll down the web page
    if loadDelay < 0:
        loadDelay = defaultValuesDict["load_content_delay"]
    verticalPosition = 0
    finishedScrolling = False
    while not finishedScrolling:
        ## Scroll live web page
        if verticalPosition < currentScrollHeight:
            webPageDriver.execute_script(scrollDownScript)
        elif verticalPosition == currentScrollHeight and previousScrollHeight != currentScrollHeight:
            ### Get new scroll height
            previousScrollHeight = currentScrollHeight
            time.sleep(loadDelay)
            currentScrollHeight = webPageDriver.execute_script(getScrollHeightScript)
        
        musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
        
        verticalPosition = verticalPosition + 1

def scrollTo(driver, x, y):
    scrollToScript = """window.scrollTo(%s, %s)"""%(x, y)
    driver.execute_script(scrollToScript)

def scrollDown(driver, distance):
    scrollDownScript = """window.scrollBy(0, %s)"""%(distance)
    driver.execute_script(scrollDownScript)

def scrollWebPageToTopNoDelay(webPageDriver):
    scrollUpScript = """window.scroll(0, 0)"""
    webPageDriver.execute_script(scrollUpScript)
    
def scrollWebPageToBottomNoDelay(webPageDriver):
    getScrollHeightScript = """return document.body.scrollHeight"""
    scrollHeight = webPageDriver.execute_script(getScrollHeightScript)
    scrollUpScript = """window.scroll(0, %s)"""%(scrollHeight)
    webPageDriver.execute_script(scrollUpScript)



# This function assumes that the web drivers are not switched to the replay iframe for ReplayWeb.page
def scrollWebPages(liveWebPageWindowDriver, replayWindowDriverList, replaySystem, livestreamSettings, defaultValuesDict, initialXpos=0, initialYpos=0, scrollElements=False, maxFrameDepth=10, framePathList=None, willPlayMusic=False, musicDriver=None, musicDF=None, musicInfo=None, localServerPortNum=None, currentMusicGenre="all", prevMusicIndexList=None, delayBetweenTracks=0, scrollTimeout=300, startTime=None):
    
    musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
    
    if startTime == None:
        startScrollTime = datetime.datetime.utcnow()
    else:
        startScrollTime = startTime
    
    getScrollHeightScript = """return document.body.scrollHeight"""
    getScrollWidthScript = """return document.body.scrollWidth"""
    scrollDownScript = """window.scrollBy(0, 1)"""
    
    if framePathList == None:
        framePathList = []
    
    if initialXpos < 0:
        initialXpos = 0
    
    if initialYpos < 0:
        initialYpos = 0
    
    # Get the scroll heights for each window and scroll to the initial position
    ## Live web page
    currentLiveScrollHeight = liveWebPageWindowDriver.execute_script(getScrollHeightScript)
    currentLiveScrollWidth = liveWebPageWindowDriver.execute_script(getScrollWidthScript)
    liveWebPageWindowDriver.execute_script("""window.scrollTo(%s,%s);"""%(min(initialXpos, currentLiveScrollWidth), min(initialYpos, currentLiveScrollHeight))) # Make the page go to initial position
    previousLiveScrollHeight = 0
    ## Replayed web page
    currentReplayScrollHeightList = []
    previousReplayScrollHeightList = []
    currentReplayScrollWidthList = []
    replayWindowFinishedList = []
    hasSwitchedToFrameList = []
    loadTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
    for replayWindowIndex in range(len(replayWindowDriverList)):
        if loadTimeDuration >= scrollTimeout:
            return # Exit the function
        
        replayWindowDriver = replayWindowDriverList[replayWindowIndex]
        hasSwitchedToFrameList.append(switchToReplayIframe(replayWindowDriver, replaySystem))
        currentReplayScrollHeightList.append(replayWindowDriver.execute_script(getScrollHeightScript))
        currentReplayScrollWidthList.append(replayWindowDriver.execute_script(getScrollWidthScript))
        replayWindowDriver.execute_script("""window.scrollTo(%s,%s);"""%(min(initialXpos, currentReplayScrollWidthList[-1]), min(initialYpos, currentReplayScrollHeightList[-1]))) # Make the page go to initial position
        previousReplayScrollHeightList.append(0)
        replayWindowFinishedList.append(not hasSwitchedToFrameList[replayWindowIndex])
        
        loadTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
    
    musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
    
    
    # Scroll down the web pages
    loadDelay = defaultValuesDict["load_content_delay"]
    verticalPosition = 0
    while False in replayWindowFinishedList:
        #print("replayWindowFinishedList:" + str(replayWindowFinishedList))
        ## Scroll live web page
        currentLiveScrollHeight = liveWebPageWindowDriver.execute_script(getScrollHeightScript)
        if verticalPosition < currentLiveScrollHeight:
            liveWebPageWindowDriver.execute_script(scrollDownScript)
        elif verticalPosition >= currentLiveScrollHeight and previousLiveScrollHeight != currentLiveScrollHeight:
            ### Get new scroll height
            previousLiveScrollHeight = currentLiveScrollHeight
            time.sleep(loadDelay)
            
        
        ## Scroll replayed web page
        numReplayWindowsFinished = 0
        for replayWindowIndex in range(len(replayWindowDriverList)):
            
            # Check if an archived web page is being replayed
            if not hasSwitchedToFrameList[replayWindowIndex]:
                continue
            
            replayWindowDriver = replayWindowDriverList[replayWindowIndex]
            currentReplayScrollHeightList[replayWindowIndex] = replayWindowDriver.execute_script(getScrollHeightScript)
            if verticalPosition < currentReplayScrollHeightList[replayWindowIndex] and hasSwitchedToFrameList[replayWindowIndex]:
                replayWindowFinishedList[replayWindowIndex] = False
                replayWindowDriver.execute_script(scrollDownScript)
            elif previousReplayScrollHeightList[replayWindowIndex] == currentReplayScrollHeightList[replayWindowIndex]:
                replayWindowFinishedList[replayWindowIndex] = True
            elif verticalPosition >= currentReplayScrollHeightList[replayWindowIndex] and hasSwitchedToFrameList[replayWindowIndex]:
                ### Get new scroll height
                previousReplayScrollHeightList[replayWindowIndex] = currentReplayScrollHeightList[replayWindowIndex]
                time.sleep(loadDelay)
                #currentReplayScrollHeightList[replayWindowIndex] = replayWindowDriver.execute_script(getScrollHeightScript)
                
        musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
        
        verticalPosition = verticalPosition + 1
        
        scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
        if (scrollTimeDuration + loadDelay) >= scrollTimeout:
            # stop scrolling and exit the function
            time.sleep(loadDelay) # Have a short delay before exiting the function
            return
    
    scrollTimeDuration = int( (datetime.datetime.utcnow() - startScrollTime).total_seconds() )
    if scrollElements and scrollTimeDuration < scrollTimeout:
        ## Initialize the prevScrollableElements
        prevScrollableElements = []
        ### Live
        prevScrollableElements.append({"driver": liveWebPageWindowDriver, "element_list": []})
        ### Replayed web pages
        for replayWindowIndex in range(len(replayWindowDriverList)):
            
            # Check if an archived web page is being replayed
            if not hasSwitchedToFrameList[replayWindowIndex]:
                continue
            
            prevScrollableElements.append({"driver": replayWindowDriverList[replayWindowIndex], "element_list": []})
        
        finishedScrolling = False
        while not finishedScrolling:
            finishedScrolling = True
            maxElementListSize = 0
            try:
                musicInfo, musicDuration = checkMusic(willPlayMusic, musicDriver, musicDF, musicInfo, localServerPortNum, currentGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks)
                
                ## Get the element lists
                ### Live
                sortedScrollableElements = []
                sortedScrollableElements.append({"driver":liveWebPageWindowDriver, "element_list": getSortedScrollableElementsList(liveWebPageWindowDriver)})
                #maxElementListSize = len(sortedScrollableElements[-1]["element_list"])# maxElementListSize cannot be set based on live web page, because the live web can generate more dynamic content than the archived web pages
                ### Replayed web pages
                for replayWindowIndex in range(len(replayWindowDriverList)):
                    
                    # Check if an archived web page is being replayed
                    if not hasSwitchedToFrameList[replayWindowIndex]:
                        continue
                    
                    sortedScrollableElements.append({"driver":replayWindowDriverList[replayWindowIndex], "element_list": getSortedScrollableElementsList(replayWindowDriverList[replayWindowIndex])})
                    
                    ### Update the maximum element list size after a new element list is added
                    maxElementListSize = max(maxElementListSize, len(sortedScrollableElements[-1]["element_list"]))
                    
                for currentElementIndex in range(maxElementListSize):
                    ## Scroll the elements with the same element index
                    for currentDictIndex in range(len(sortedScrollableElements)):
                        currentElement = None
                        if currentElementIndex < len(sortedScrollableElements[currentDictIndex]["element_list"]):
                            currentElement = sortedScrollableElements[currentDictIndex]["element_list"][currentElementIndex]
                            currentDriver = sortedScrollableElements[currentDictIndex]["driver"]
                        
                        if currentElement != None and currentElementIndex not in prevScrollableElements[currentDictIndex]["element_list"]:
                            finishedScrolling = scrollElementToBottom(currentDriver, currentElement, scrollFrames=True, maxFrameDepth=maxFrameDepth, framePathList=framePathList, willPlayMusic=willPlayMusic, musicDriver=musicDriver, musicDF=musicDF, musicInfo=musicInfo, localServerPortNum=localServerPortNum, currentMusicGenre=currentMusicGenre, prevMusicIndexList=prevMusicIndexList, delayBetweenTracks=delayBetweenTracks, scrollTimeout=scrollTimeout, startScrollTime=startScrollTime)
                            #if not finishedScrolling:
                            #   continue # Check if the current element was able to be scrolled, skip this element if it failed. Will attempt to scroll again later during the next iteration of the outer loop
                            prevScrollableElements[currentDictIndex]["element_list"].append(currentElementIndex) # Decided to use the index instead of the element, because the element may be dynamically changed by JavaScript
            except:
                finishedScrolling = False

def detectPlatform(url):
    platforms = ["https://www.youtube.com/", "https://www.twitch.tv/", "https://www.facebook.com/", "https://twitter.com/"]
    
    if surt(platforms[0]) in surt(url):
        currentPlatform = "YouTube"
    elif surt(platforms[1]) in surt(url):
        currentPlatform = "Twitch"
    elif surt(platforms[2]) in surt(url):
        currentPlatform = "Facebook"
    elif surt(platforms[3]) in surt(url):
        currentPlatform = "Twitter"
    
    return currentPlatform

# Get chat messages from YouTube without API
def getChatMessages():
    time.sleep(30) # wait for the web page to load
    driver.switch_to.default_content() # Make sure driver is not in a different iframe
    driver.switch_to.frame("chatframe") # iframe where chat messages are
    spans = driver.find_elements(By.TAG_NAME, "span")
    messages = []
    print("Number of spans: " + str(len(spans)))
    for i in range(len(spans)):
        if "yt-live-chat-text-message-renderer" in spans[i].get_attribute("class"):
            messages.append(spans[i].get_attribute("innerHTML"))
    
    return messages
    
"""
    A chat message has three spans associated with it for YouTube which are the post time, text for chat message, and delete state. I will replace the delete state with the author name.
"""
def getAuthors():
    driver.switch_to.default_content() # Make sure driver is not in a different iframe
    driver.switch_to.frame("chatframe") # iframe where chat messages are
    spans = driver.find_elements(By.TAG_NAME, "span")
    
    authors = []
    for i in range(len(spans)):
        if "yt-live-chat-author-chip" in spans[i].get_attribute("class") and "author-name" in spans[i].get_attribute("id"):
            currentAuthor = spans[i].get_attribute("innerHTML").split("<span")[0]#For YouTube
            authors.append(currentAuthor)
    
    return authors
    
"""
    Currently the tuple that will be returned is: (time, author, message, delete state)
"""
def convertMessageListToTuple(messages, authors):
    messageTupleList = []
    for i in range(0, len(messages) - 2, 3):
        currentTuple = (messages[i], authors[i//3], messages[i + 1], messages[i + 2])
        messageTupleList.append(currentTuple)
    return messageTupleList

#Gets the URLs from the live chat for YouTube
#The tuple that will be returned is: (time, author, URL)
def getURLRequests():
    # Get the messages
    messages = getChatMessages()
    authors = getAuthors()
    messageTupleList = convertMessageListToTuple(messages, authors)
    
    # Currently there are three span elements for each chat message
    ## Time of chat message, text for chat message, deleted state (replace this with username)
    urlRequests = []
    for i in range(len(messageTupleList)):
        requestTime = messageTupleList[i][0]
        currentAuthor = messageTupleList[i][1]
        currentMessage = messageTupleList[i][2]
        
        print("\nAuthor: " + currentAuthor)
        print("Message: " + currentMessage)
        
        requestedUrl = currentMessage.strip().replace(' ', '.')
        if not("http" in requestedUrl):
            requestedUrl = "https://" + requestedUrl
        else:
            requestedUrl = requestedUrl.replace('http.', 'http://')
            requestedUrl = requestedUrl.replace('https.', 'https://')
            
        
        try:
            response = requests.get(requestedUrl)
            requestedUrl = response.url
            print("URL: " + requestedUrl)
            print("Status code: " + str(response.status_code))
            
            if(response.status_code == 200):
                urlRequests.append((requestTime, currentAuthor, requestedUrl))
        except:
            print("Not a URL")
        
        print("Time of request: " + requestTime)
    
    return urlRequests

def getPageStatus(requestedUrl):
    response = requests.get(requestedUrl)
    requestedUrl = response.url
    return response.status_code


def getKnownCrawlerDict_GunMayhem2(name="default"):
    knownCrawlersList = []
    knownCrawlersList.append({
        "name": "Wayback Machine",
        "hat_number": 13,
        "face_number": 1,
        "shirt_number": 4,
        "color_number": 4
    })
    knownCrawlersList.append({
        "name": "Brozzler",
        "hat_number": 3,
        "face_number": 1,
        "shirt_number": 2,
        "color_number": 15
    })
    knownCrawlersList.append({
        "name": "Browsertrix",
        "hat_number": 5,
        "face_number": 9,
        "shirt_number": 5,
        "color_number": 12
    })
    
    knownCrawlersList.append({
        "name": "Squidwarc",
        "hat_number": 16,
        "face_number": 2,
        "shirt_number": 13,
        "color_number": 18
    })

    knownCrawlersList.append({
        "name": "wget",
        "hat_number": 1,
        "face_number": 4,
        "shirt_number": 6,
        "color_number": 11
    })

    for crawlerDict in knownCrawlersList:
        if name.lower() == crawlerDict["name"].lower():
            return crawlerDict
    
    return {"name": "Default", "hat_number": 1, "face_number": 1, "shirt_number": 1, "color_number": 1}



def getVertPosDict(livestreamSettings, defaultValuesDict, setSize):
    if "archive_stage_heading" in livestreamSettings:
        stageHeadingText = livestreamSettings["archive_stage_heading"]
    else:
        stageHeadingText = """Web Archiving Speedrun (%s Web Pages To Archive)"""%(setSize) #"Archiving A Set Of URLs"

    # Move the stage info window to its expected location
    # Determine the vertical alignment for each type of window
    verticalPosDict = {}
    if "stage_info_window_vertical_alignment" in livestreamSettings:
        verticalPosDict[livestreamSettings["stage_info_window_vertical_alignment"]] = "stage_info_window"
    if "crawler_info_window_vertical_alignment" in livestreamSettings:
        verticalPosDict[livestreamSettings["crawler_info_window_vertical_alignment"]] = "crawler_info_window"
    if "crawler_browser_window_vertical_alignment" in livestreamSettings:
        verticalPosDict[livestreamSettings["crawler_browser_window_vertical_alignment"]] = "crawler_browser_window"
    
    ## Check if any of the windows were not added to the vertical alignment dictionary
    ### Stage info window
    if "use_stage_info_window" not in livestreamSettings or livestreamSettings["use_stage_info_window"] == True:
        if "stage_info_window" not in list(verticalPosDict.values()):
            if defaultValuesDict["stage_info_window_vertical_alignment"] not in verticalPosDict:
                verticalPosDict[defaultValuesDict["stage_info_window_vertical_alignment"]] = "stage_info_window"
            elif "top_window" not in verticalPosDict:
                verticalPosDict["top_window"] = "stage_info_window"
            elif "bottom_window" not in verticalPosDict:
                verticalPosDict["bottom_window"] = "stage_info_window"
            elif "center_window" not in verticalPosDict:
                verticalPosDict["center_window"] = "stage_info_window"
                
    ### Crawler info window
    if "use_crawler_info_window" not in livestreamSettings or livestreamSettings["use_crawler_info_window"] == True:
        if "crawler_info_window" not in list(verticalPosDict.values()):
            if defaultValuesDict["crawler_info_window_vertical_alignment"] not in verticalPosDict:
                verticalPosDict[defaultValuesDict["crawler_info_window_vertical_alignment"]] = "crawler_info_window"
            elif "top_window" not in verticalPosDict:
                verticalPosDict["top_window"] = "crawler_info_window"
            elif "bottom_window" not in verticalPosDict:
                verticalPosDict["bottom_window"] = "crawler_info_window"
            elif "center_window" not in verticalPosDict:
                verticalPosDict["center_window"] = "crawler_info_window"
                
    ### Crawler browser window
    if "crawler_browser_window" not in list(verticalPosDict.values()):
        if defaultValuesDict["crawler_browser_window_vertical_alignment"] not in verticalPosDict:
            verticalPosDict[defaultValuesDict["crawler_browser_window_vertical_alignment"]] = "crawler_browser_window"
        elif "top_window" not in verticalPosDict:
            verticalPosDict["top_window"] = "crawler_browser_window"
        elif "bottom_window" not in verticalPosDict:
            verticalPosDict["bottom_window"] = "crawler_browser_window"
        elif "center_window" not in verticalPosDict:
            verticalPosDict["center_window"] = "crawler_browser_window"

    return verticalPosDict

# Move the windows to their expected positions based on verticalPosDict
def moveWindows(verticalPosDict, livestreamSettings, defaultValuesDict, commandWindowCrawlers, crawlerNameList, stageInfoDriver, crawlerInfoDriverList, crawlerBrowserDriverList, screenWidth, screenHeight, setupStageInfoDriver=False):
    # Set the horizontal alginment for stage info window
    if "stage_info_window_horizontal_alignment" in livestreamSettings:
        stageInfoWindowHorizontalAlignment = livestreamSettings["stage_info_window_horizontal_alignment"]
    else:
        stageInfoWindowHorizontalAlignment = defaultValuesDict["stage_info_window_horizontal_alignment"]
    
    ## Top window
    currentWindowVerticalAlignment = "top"
    if verticalPosDict["top_window"].lower() == "stage_info_window" and setupStageInfoDriver:
        windowType = "stage_info_window"
        stageInfoDriver = setupWindow(windowType, livestreamSettings, defaultValuesDict, stageInfoWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)
        
        topWindowDriver = stageInfoDriver
    elif verticalPosDict["top_window"].lower() == "crawler_info_window":
        windowType = "crawler_info_window"
        ## Move crawler info windows
        for index in range(len(crawlerNameList)):
            if index > 0 and index != len(crawlerNameList) - 1:
                currentWindowHorizontalAlignment = "center"
                leftWindowX = crawlerInfoDriverList[index - 1].get_window_position()["x"]
                leftWindowWidth =  crawlerInfoDriverList[index - 1].get_window_size()["width"]
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, screenWidth=screenWidth, screenHeight=screenHeight)
            elif index == 0:
                currentWindowHorizontalAlignment = "left"
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)
            else:
                currentWindowHorizontalAlignment = "right"
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)

        topWindowDriver = crawlerInfoDriverList[0]
    elif verticalPosDict["top_window"].lower() == "crawler_browser_window":
        windowType = "crawler_browser_window"
        ## Move crawler browser windows
        for index in range(len(crawlerNameList)):
            if crawlerNameList[index].lower() not in commandWindowCrawlers:
                appDriver = False
            else:
                appDriver = True
            if index > 0 and index != len(crawlerNameList) - 1:
                currentWindowHorizontalAlignment = "center"
                leftWindowX = crawlerBrowserDriverList[index - 1].get_window_position()["x"]
                leftWindowWidth =  crawlerBrowserDriverList[index - 1].get_window_size()["width"]
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, screenWidth=screenWidth, screenHeight=screenHeight)
            elif index == 0:
                currentWindowHorizontalAlignment = "left"
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, screenWidth=screenWidth, screenHeight=screenHeight)
            else:
                currentWindowHorizontalAlignment = "right"
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, screenWidth=screenWidth, screenHeight=screenHeight)
        
        topWindowDriver = crawlerBrowserDriverList[0]

    ## Center window
    currentWindowVerticalAlignment = "center"
    if topWindowDriver != None:
        if verticalPosDict["center_window"].lower() == "stage_info_window" and setupStageInfoDriver:
            windowType = "stage_info_window"
            stageInfoDriver = setupWindow(windowType, livestreamSettings, defaultValuesDict, stageInfoWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
            
            centerWindowDriver = stageInfoDriver
        elif verticalPosDict["center_window"].lower() == "crawler_info_window":
            windowType = "crawler_info_window"
            ## Move crawler info windows
            for index in range(len(crawlerNameList)):
                if index > 0 and index != len(crawlerNameList) - 1:
                    currentWindowHorizontalAlignment = "center"
                    leftWindowX = crawlerInfoDriverList[index - 1].get_window_position()["x"]
                    leftWindowWidth =  crawlerInfoDriverList[index - 1].get_window_size()["width"]
                    crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
                elif index == 0:
                    currentWindowHorizontalAlignment = "left"
                    crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
                else:
                    currentWindowHorizontalAlignment = "right"
                    crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
            
            centerWindowDriver = crawlerInfoDriverList[0]
        elif verticalPosDict["center_window"].lower() == "crawler_browser_window":
            windowType = "crawler_browser_window"
            ## Move crawler browser windows
            for index in range(len(crawlerNameList)):
                if crawlerNameList[index].lower() not in commandWindowCrawlers:
                    appDriver = False
                else:
                    appDriver = True
                if index > 0 and index != len(crawlerNameList) - 1:
                    currentWindowHorizontalAlignment = "center"
                    leftWindowX = crawlerBrowserDriverList[index - 1].get_window_position()["x"]
                    leftWindowWidth =  crawlerBrowserDriverList[index - 1].get_window_size()["width"]
                    crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
                elif index == 0:
                    currentWindowHorizontalAlignment = "left"
                    crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
                else:
                    currentWindowHorizontalAlignment = "right"
                    crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, aboveWindowHeight=topWindowDriver.get_window_size()["height"], aboveWindowY=topWindowDriver.get_window_position()["y"], screenWidth=screenWidth, screenHeight=screenHeight)
            
            centerWindowDriver = crawlerBrowserDriverList[0]
    else:
        print("There needs to be a window aligned to the top of the screen.")
        exit()

    ## Bottom window
    currentWindowVerticalAlignment = "bottom"
    if verticalPosDict["bottom_window"].lower() == "stage_info_window" and setupStageInfoDriver:
        windowType = "stage_info_window"
        stageInfoDriver = setupWindow(windowType, livestreamSettings, defaultValuesDict, stageInfoWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)
        
        bottomWindowDriver = stageInfoDriver
    elif verticalPosDict["bottom_window"].lower() == "crawler_info_window":
        windowType = "crawler_info_window"
        ## Move crawler info windows
        for index in range(len(crawlerNameList)):
            if index > 0 and index != len(crawlerNameList) - 1:
                currentWindowHorizontalAlignment = "center"
                leftWindowX = crawlerInfoDriverList[index - 1].get_window_position()["x"]
                leftWindowWidth =  crawlerInfoDriverList[index - 1].get_window_size()["width"]
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, screenWidth=screenWidth, screenHeight=screenHeight)
            elif index == 0:
                currentWindowHorizontalAlignment = "left"
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)
            else:
                currentWindowHorizontalAlignment = "right"
                crawlerInfoDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=True, screenWidth=screenWidth, screenHeight=screenHeight)
        
        bottomWindowDriver = crawlerInfoDriverList[0]
    elif verticalPosDict["bottom_window"].lower() == "crawler_browser_window":
        windowType = "crawler_browser_window"
        ## Move crawler browser windows
        for index in range(len(crawlerNameList)):
            if crawlerNameList[index].lower() not in commandWindowCrawlers:
                appDriver = False
            else:
                appDriver = True
            if index > 0 and index != len(crawlerNameList) - 1:
                currentWindowHorizontalAlignment = "center"
                leftWindowX = crawlerBrowserDriverList[index - 1].get_window_position()["x"]
                leftWindowWidth =  crawlerBrowserDriverList[index - 1].get_window_size()["width"]
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, leftWindowWidth=leftWindowWidth, leftWindowX=leftWindowX, screenWidth=screenWidth, screenHeight=screenHeight)
            elif index == 0:
                currentWindowHorizontalAlignment = "left"
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, screenWidth=screenWidth, screenHeight=screenHeight)
            else:
                currentWindowHorizontalAlignment = "right"
                crawlerBrowserDriverList[index] = setupWindow(windowType, livestreamSettings, defaultValuesDict, currentWindowHorizontalAlignment, currentWindowVerticalAlignment, appDriver=appDriver, screenWidth=screenWidth, screenHeight=screenHeight)
        
        bottomWindowDriver = crawlerBrowserDriverList[0]
        
        if setupStageInfoDriver:
            return stageInfoDriver
        else:
            return None

def setupAllWindows(livestreamSettings, defaultValuesDict, commandWindowCrawlers, crawlerNameList, stageInfoDriver, crawlerInfoDriverList, crawlerBrowserDriverList, screenWidth, screenHeight, setupStageInfoDriver=False):
    verticalPosDict = getVertPosDict(livestreamSettings, defaultValuesDict, setSize)
    return moveWindows(verticalPosDict, livestreamSettings, defaultValuesDict, commandWindowCrawlers, crawlerNameList, stageInfoDriver, crawlerInfoDriverList, crawlerBrowserDriverList, screenWidth, screenHeight, setupStageInfoDriver=setupStageInfoDriver)
        

