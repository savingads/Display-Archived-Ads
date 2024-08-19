# Travis Reid

from WAL_Utilities import *
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from enum import unique
from warcio.archiveiterator import ArchiveIterator
import sys
from surt import surt
import time
import subprocess
import os
from pathlib import Path
import shutil

def printFilteredContentTypes(uniqueFilteredContentTypes):
    print("Content type not listed:")
    for contentType in uniqueFilteredContentTypes:
        print(contentType)

def printAllowedContentTypes(uniqueAllowedContentTypes):
    print("Content types allowed:")
    for contentType in uniqueAllowedContentTypes:
        print(contentType)

def printUrlsWithoutAContentType(urlsWithoutAContentType):
    print("URLs without a content type:")
    for url in urlsWithoutAContentType:
        print(url)        

def printPotentialAdUrls(potentialAdUrlsDict):
    print("Potential Ad URLs (" + str(len(potentialAdUrlsDict)) + ") :")
    for key in potentialAdUrlsDict.keys():
        for urlIndex in len(potentialAdUrlsDict[key]):
            url = potentialAdUrlsDict[key][urlIndex]["url"]
            print(url)                

def initAdContentTypes(potentialAdUrlsDict, adContentList):
    for contentType in adContentList:
        potentialAdUrlsDict[contentType] = []


# Modified function from web archiving livestream script
def getEmbeddedReplayWebPageCode(warcFilePath, url, settings, defaultValuesDict):
    if "replay_web_page_version" in settings:
        replayWebPageVersion = settings["replay_web_page_version"]
    else:
        replayWebPageVersion = defaultValuesDict["replay_web_page_version"]
    
    # Move a copy of the warc file to the current directory
    try:
        copiedWarcFilePath = os.path.abspath(os.getcwd()) + "/" + os.path.basename(warcFilePath)
        if os.path.exists(copiedWarcFilePath):
            copiedWarcFilePath = None
        
        filePath, fileExtension = os.path.splitext(warcFilePath)
        fileName = filePath.split("/")[-1] + fileExtension
        subprocess.run("""cp %s %s"""%(warcFilePath, os.path.abspath(os.getcwd()) + "/" + fileName), shell=True)
        relWarcFilePath = os.path.relpath(os.path.abspath(os.getcwd()) + "/" + fileName)
    except:
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
    
    
    if "replay_web_page_embed_type" in settings:
        embedType = settings["replay_web_page_embed_type"]
    else:
        embedType = defaultValuesDict["replay_web_page_embed_type"]
    webPageCode = """<html><head><script src="https://cdn.jsdelivr.net/npm/replaywebpage@%s/ui.js"></script></head><body><replay-web-page source="%s" url="%s" embed="%s"></replay-web-page></body></html>"""%(replayWebPageVersion, relWarcFilePath, url, embedType)

    # Return the HTML code needed for ad URI-M iframe
    return webPageCode
    
    #webPage = "http://127.0.0.1:" + portNum + "/" + htmlFileName
    

def addURLToAdList(potentialAdUrlsDict, currentURL, currentContentTypeSplit, adContentList, warcFilePath, replaySettings, defaultValuesDict):
    if currentContentTypeSplit[0] in adContentList:
        contentType = currentContentTypeSplit[0]
    elif currentContentTypeSplit[1] in adContentList:
        contentType = currentContentTypeSplit[1]
    else:
        return
    
    '''
    if "replay_web_page_port_number" in replaySettings:
        portNum = replaySettings["replay_web_page_port_number"]
    else:
        portNum = defaultValuesDict["replay_web_page_port_number"]

    webPageCode = getEmbeddedReplayWebPageCode(warcFilePath, currentURL, replaySettings, defaultValuesDict)
    currentHtmlFileName = str(len(potentialAdUrlsDict[contentType])) + ".html"
    currentHtmlFile = open(str(os.getcwd()) + "/" + str(currentHtmlFileName), "w")
    currentHtmlFile.write(webPageCode)
    currentHtmlFile.close()
    '''
    resourceDict = {"url": currentURL, "type": ("/").join(currentContentTypeSplit)}
    potentialAdUrlsDict[contentType].append(resourceDict)

def displayPotentialAds(potentialAdUrlsDict, replaySettings, defaultValuesDict, warcFilePath, adContentList):
    # Start the simple server
    #simpleServerProcess = startSimpleServer(replaySettings, defaultValuesDict)
    ts = int(time.time())
    subprocess.run(["wb-manager init my-web-archive-%s"%(ts) ], shell=True)
    #print(os.path.abspath(warcFilePath))
    subprocess.run(["wb-manager add my-web-archive-%s %s"%(ts, os.path.abspath(warcFilePath))], shell=True)
    pywbProcess = subprocess.Popen(["wayback"], shell=True)

    driver = createGeneralWebDriver()
    driver.maximize_window()

    displayPotentialAdsScript ="""
    var potentialAdUrlsObj = %s;
    var categoryList = %s;
    var ts = %s;
    var pctChar = "%s";
    var resizeDelay = 1000;
    var localhost = "http://localhost:8080/my-web-archive-"+ ts + "/mp_/";
    var numResourcesOptionsList = [1, 5, 10];

    const delay = ms => new Promise(res => setTimeout(res, ms));
    
    function getClearedMainDiv()
    {
        //Remove the old mainDiv and replace with a new one
        var mainDiv = document.getElementById("main_div");
        mainDiv.innerHTML = "";
        var tempDiv = mainDiv.cloneNode(true);
        mainDiv.remove();
        mainDiv = tempDiv;
        document.body.appendChild(mainDiv);
        return mainDiv;   
    }

    function getClonedDiv(divID)
    {
        //Remove the old div and replace with a new one
        var div = document.getElementById(divID);
        var tempDiv = div.cloneNode(true);
        var divIndex = Array.prototype.indexOf.call(div.parentElement.children, div);
        div.remove();
        div = tempDiv;
        document.body.insertBefore(div, document.body.children[divIndex]);
        return div;   
    }

    function updateButtonRow(buttonRowDiv, selectedButtonIndex, optionType, potentialAdUrlsObj, startIndex)
    {
        //Update page numbers and selectedButtonIndex if the button row is associated with page selection
        if(optionType.toLowerCase() == "page_selection")
        {
            var mainDiv = document.getElementById("main_div");
            var category = mainDiv.getAttribute("category");
            var numberResourcesDisplayed = parseInt(mainDiv.getAttribute("number_of_resources_displayed"));
            var pageNum = Math.ceil((startIndex + 1) / numberResourcesDisplayed);
            var lastPageNum = Math.ceil(potentialAdUrlsObj[category].length / numberResourcesDisplayed);

            ///Can the number be centered (not centered: pageNum <= 6 or (6 < pageNum && (pageNum + 4) >= lastPageNum) )
            var leftmostNum, rightmostNum, numButtons, maxNumButtons = 10;
            if (pageNum <= 6) 
            {
                leftmostNum = Math.max(1, pageNum - 5);
                rightmostNum = Math.min(leftmostNum + 9, lastPageNum);
            }
            else if(6 < pageNum && (pageNum + 4) >= lastPageNum)
            {
                rightmostNum = Math.min(pageNum + 4, lastPageNum);
                leftmostNum = Math.max(1, rightmostNum - 9);
            }
            else // This case adjust the leftmost and rightmost buttons so that the current button is centered
            {
                leftmostNum = Math.max(1, pageNum - 5);
                rightmostNum = Math.min(pageNum + 4, lastPageNum);
            }
            
            selectedButtonIndex = (pageNum - leftmostNum) + 1;
            numButtons = rightmostNum - leftmostNum + 1;

            
            
            //Set the numbers for the buttons
            ///Start at 1 since there is a previous button at index 0 
            var paginationButtonRow = document.getElementById("pagination_div");//getClonedDiv("pagination_div");

            for(var pageButtonIndex = 1; pageButtonIndex < numButtons + 1; pageButtonIndex++)
            {
                var currentButton = paginationButtonRow.children[pageButtonIndex];
                var updatedNumber = leftmostNum + pageButtonIndex - 1;
                currentButton.innerHTML = updatedNumber;
                currentButton.setAttribute("option_value", updatedNumber);
                currentButton.style.display = "inline-block";
            }

            //Hide the buttons that are not needed
            for(var pageButtonIndex = numButtons + 1; pageButtonIndex < maxNumButtons + 1; pageButtonIndex++)
            {
                var currentButton = paginationButtonRow.children[pageButtonIndex];
                var updatedNumber = -1;
                currentButton.innerHTML = updatedNumber;
                currentButton.setAttribute("option_value", updatedNumber);
                currentButton.style.display = "none";
            }
        }
        
        // Update button colors if a valid index was given
        if(selectedButtonIndex === -1)
            return; //exit the function

        var firstButtonIndex = 0;
        if(optionType.toLowerCase() == "number_of_resources_displayed")
        {
            firstButtonIndex = 1;
        }
        for(var i = firstButtonIndex; i < buttonRowDiv.children.length; i++)
        {
            buttonRowDiv.children[i].style.background = "gainsboro";
            buttonRowDiv.children[i].style.color = "black";
        }
        ///Change the color of the selected button
        buttonRowDiv.children[selectedButtonIndex].style.background = "darkgreen";
        buttonRowDiv.children[selectedButtonIndex].style.color = "white";        
    }

    function updateAllButtonRows(selectedButtonDict, potentialAdUrlsObj, startIndex)
    {
        var categoryButtonRow = document.getElementById("category_option_div"); //getClonedDiv("category_option_div");
        var numResourcesButtonRow = document.getElementById("num_resources_option_div"); //getClonedDiv("num_resources_option_div");
        var paginationButtonRow = document.getElementById("pagination_div"); //getClonedDiv("pagination_div");

        updateButtonRow(categoryButtonRow, selectedButtonDict["category_button_index"], "category", potentialAdUrlsObj, startIndex);
        updateButtonRow(numResourcesButtonRow, selectedButtonDict["number_of_resources_displayed_button_index"], "number_of_resources_displayed", potentialAdUrlsObj, startIndex);
        updateButtonRow(paginationButtonRow, selectedButtonDict["page_number_button_index"], "page_selection", potentialAdUrlsObj, startIndex);
    }
    

    const displayResourcesFromCategory = async(potentialAdUrlsObj, category, startIndex=0, numberResourcesDisplayed=-1, resizeDelay=1000) =>
    {
        var mainDiv = getClearedMainDiv();

        if(potentialAdUrlsObj[category].length === 0)
        {
            var h = document.createElement("h1");
            h.innerHTML = "There are no resources for this category";
            mainDiv.appendChild(h);
            mainDiv.setAttribute("start_index", 0);
            return;
        }

        //Update startIndex to the first index on the current page and set the end index
        
        if(numberResourcesDisplayed === -1)
            numberResourcesDisplayed = parseInt(mainDiv.getAttribute("number_of_resources_displayed"));
        var pageNum = Math.ceil((startIndex + 1) / numberResourcesDisplayed);
        startIndex =  ( numberResourcesDisplayed * (pageNum - 1) );
        var endPos = Math.min(potentialAdUrlsObj[category].length, (startIndex + numberResourcesDisplayed));
        mainDiv.setAttribute("start_index", startIndex);
        mainDiv.setAttribute("end_index", endPos - 1);
        
        for(let urlIndex = startIndex; urlIndex < endPos; urlIndex++)
        {
            var heading = document.createElement("h1");
            heading.innerHTML = potentialAdUrlsObj[category][urlIndex]["url"];
            mainDiv.appendChild(heading);
            heading.style.textAlign = "center";
            heading.style.width = "98" + pctChar;
            heading.style.display = "inline-block";
            heading.style.borderTop = "0.5rem solid black";
            heading.style.padding = "1rem";

            var liveResourceHeading = document.createElement("h2");
            liveResourceHeading.style.fontSize = "160" + pctChar;
            liveResourceHeading.innerHTML = "Live Resource";
            mainDiv.appendChild(liveResourceHeading);
            liveResourceHeading.style.float = "left"; 
            liveResourceHeading.style.textAlign = "center";
            liveResourceHeading.style.width = "50" + pctChar;
            liveResourceHeading.style.margin = "0";

            var archivedResourceHeading = document.createElement("h2");
            archivedResourceHeading.style.fontSize = "160" + pctChar;
            archivedResourceHeading.innerHTML = "Archived Resource (Using pywb)";
            mainDiv.appendChild(archivedResourceHeading);
            archivedResourceHeading.style.float = "right"; 
            archivedResourceHeading.style.textAlign = "center";
            archivedResourceHeading.style.width = "50" + pctChar;            
            archivedResourceHeading.style.margin = "0";
            mainDiv.appendChild(document.createElement("br"));

            var currentElement;
            if(category.includes("web page") || category.includes("page") || category.includes("html") || category.includes("frame"))
            {
                currentElement = document.createElement("iframe");
                currentElement.src = potentialAdUrlsObj[category][urlIndex]["url"];
            }
            else if(category.includes("video"))
            {
                currentElement = document.createElement("video");
                var source = document.createElement("source");
                source.src = potentialAdUrlsObj[category][urlIndex]["url"];
                source.type = potentialAdUrlsObj[category][urlIndex]["type"];
                currentElement.appendChild(source);
            }
            else if(category.includes("audio"))
            {
                currentElement = document.createElement("audio");
                currentElement.src = potentialAdUrlsObj[category][urlIndex]["url"];
            }
            else if(category.includes("image") || category.includes("img"))
            {
                currentElement = document.createElement("img");
                currentElement.src = potentialAdUrlsObj[category][urlIndex]["url"];
            }
            mainDiv.appendChild(currentElement);
            await delay(resizeDelay);
            //setTimeout(() => {
            currentElement.style.padding = "0px";
            currentElement.style.margin = "0";

            var ratio = currentElement.getBoundingClientRect().height / currentElement.getBoundingClientRect().width;
            currentElement.style.float = "left"; 
            currentElement.style.width = 49  + pctChar;
            currentElement.style.height = (Math.floor(currentElement.getBoundingClientRect().width * ratio)).toString() + "px";

            var archivedResource = document.createElement("iframe");
            archivedResource.style.padding = "0px";
            archivedResource.style.margin = "0";
            archivedResource.scrolling = "no";
            archivedResource.src = localhost + potentialAdUrlsObj[category][urlIndex]["url"];
            archivedResource.style.float = "right";
            archivedResource.style.width = currentElement.style.width;
            archivedResource.style.height = currentElement.style.height;
            mainDiv.appendChild(archivedResource);
            mainDiv.appendChild(document.createElement("br"));
            //}, 0);
            //await delay(resizeDelay);

        }
        var hr = document.createElement("h1");
        hr.innerHTML  = " ";
        mainDiv.appendChild(hr);
        hr.style.textAlign = "center";
        hr.style.width = "98" + pctChar;
        hr.style.display = "inline-block";
        hr.style.borderTop = "0.5rem solid black";
        hr.style.padding = "1rem";
        
    }



    function initialSetup(potentialAdUrlsObj, categoryList, numResourcesOptionsList)
    {
        var mainStyle = document.createElement("style");
        document.body.appendChild(mainStyle);
        mainStyle.innerHTML = ".button_row{display: block; text-align: center; margin: auto; width: 40" + pctChar + ";} button{font-size: 120" + pctChar + ";}";
        
        var title = document.createElement("h1");
        title.style.fontSize = "300" + pctChar;
        title.innerHTML = "Potential Ads";
        document.body.appendChild(title);
        title.style.float = "center"; 
        title.style.textAlign = "center";
        title.style.width = "98" + pctChar;
        title.style.margin = "0";

        //Create and append all of the button rows 
        var categoryButtonRow = document.createElement("div");
        document.body.append(categoryButtonRow);
        categoryButtonRow.id = "category_option_div";
        var numResourcesButtonRow = document.createElement("div");
        document.body.append(numResourcesButtonRow);
        numResourcesButtonRow.id = "num_resources_option_div";
        var paginationButtonRow = document.createElement("div");
        document.body.append(paginationButtonRow);
        paginationButtonRow.id = "pagination_div";

        //Format the button rows
        categoryButtonRow.className = "button_row";
        numResourcesButtonRow.className = "button_row";
        paginationButtonRow.className = "button_row";

        //Add the buttons for the categories
        var numCategories = categoryList.length;
        for(var categoryIndex = 0; categoryIndex < numCategories; categoryIndex++)
        {
            var currentButton = document.createElement("button");
            categoryButtonRow.appendChild(currentButton);
            currentButton.type = "button";
            currentButton.innerHTML = categoryList[categoryIndex];
            currentButton.id = categoryList[categoryIndex];
            currentButton.setAttribute("category", categoryList[categoryIndex])
            currentButton.style.width = (Math.floor((1 / numCategories) * 100)).toString() + pctChar;
            currentButton.style.height = "auto";
            currentButton.onclick = function(){ 
                    var mainDiv = getClearedMainDiv();
                    var category = this.getAttribute("category");
                    mainDiv.setAttribute("category", category);
                    mainDiv.setAttribute("current_page", 1); //When switching categories will switch to first page

                    var totalNumResourcesText = document.getElementById("total_number_of_resources");
                    totalNumResourcesText.innerHTML = (potentialAdUrlsObj[category]).length.toString();                    
                    if(category === "html")
                    {
                        totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Web Page Ads";
                    }
                    else if(category === "video")
                    {
                        totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Video Ads";
                    }
                    else if(category === "audio")
                    {
                        totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Audio Ads";
                    }        
                    else if(category === "image")
                    {
                        totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Image Ads";
                    }                            

                    var numberResourcesDisplayed = parseInt(mainDiv.getAttribute("number_of_resources_displayed"));
                    
                    // Update the starting index and set the page number
                    var startIndex = 0;
                    mainDiv.setAttribute("start_index", startIndex);
                    
                    displayResourcesFromCategory(potentialAdUrlsObj, category, startIndex=startIndex, numberResourcesDisplayed=numberResourcesDisplayed);

                    var categoryButtonIndex = Array.prototype.indexOf.call(this.parentNode.children, this); 
                    var selectedButtonDict = {"category_button_index": categoryButtonIndex, "number_of_resources_displayed_button_index":-1, "page_number_button_index":-1};
                    updateAllButtonRows(selectedButtonDict, potentialAdUrlsObj, startIndex);
                };
        }

        for(var i = 0; i < categoryButtonRow.children.length; i++)
        {
            categoryButtonRow.children[i].style.background = "gainsboro";
            categoryButtonRow.children[i].style.color = "black";
        }

        // Add the buttons for the options associated with the number of resources displayed at once
        var numOptions = numResourcesOptionsList.length;
        var optionText = document.createElement("p");
        numResourcesButtonRow.appendChild(optionText);
        optionText.innerHTML = "Resources Displayed:";
        optionText.style.fontSize = "125" + pctChar;
        optionText.style.display = "inline-block";
        optionText.style.width = (Math.floor((1 / (numOptions + 1)) * 100)).toString() + pctChar;
        for(var optionIndex = 0; optionIndex < numOptions; optionIndex++)
        {
            var currentButton = document.createElement("button");
            numResourcesButtonRow.appendChild(currentButton);
            currentButton.type = "button";
            currentButton.innerHTML = numResourcesOptionsList[optionIndex];
            currentButton.id = numResourcesOptionsList[optionIndex];
            currentButton.setAttribute("option_value", numResourcesOptionsList[optionIndex]);
            currentButton.style.width = (Math.floor((1 / (numOptions + 1)) * 100)).toString() + pctChar;
            currentButton.style.height = "auto";
            currentButton.onclick = function(){ 
                    var mainDiv = getClearedMainDiv();
                    var numberResourcesDisplayed = parseInt(this.getAttribute("option_value"));
                    mainDiv.setAttribute("number_of_resources_displayed", numberResourcesDisplayed);
                    
                    var startIndex = parseInt(mainDiv.getAttribute("start_index")); 

                    var category = mainDiv.getAttribute("category");
                    displayResourcesFromCategory(potentialAdUrlsObj, category, startIndex=startIndex, numberResourcesDisplayed=numberResourcesDisplayed);

                    var currentButtonIndex = Array.prototype.indexOf.call(this.parentNode.children, this); 
                    var selectedButtonDict = {"category_button_index": -1, "number_of_resources_displayed_button_index": currentButtonIndex, "page_number_button_index":-1};
                    updateAllButtonRows(selectedButtonDict, potentialAdUrlsObj, startIndex);                    
                };
        }

        for(var i = 1; i < numResourcesButtonRow.children.length; i++)
        {
            numResourcesButtonRow.children[i].style.background = "gainsboro";
            numResourcesButtonRow.children[i].style.color = "black";
        }

        // Add buttons for pagination
        ///numButtons = 1(prev button) + min(10, totalNumResources / resourcesDisplayed) + 1(next button)
        //paginationButtonRow.style.width = "36" + pctChar;
        var startingCategory = categoryList[0];
        var numOptions = Math.min(10, potentialAdUrlsObj[startingCategory].length)
        var leftmostNumber = 1;
        //var rightmostNumberedButton = 10;
        
        /// Create previous and next buttons
        var maxNumPaginationButtons = 10;
        var prevButton = null;
        var nextButton = null;
        for(var i = 0; i < 2; i++)
        {
            var currentButton = document.createElement("button");
            currentButton.type = "button";
            if(i == 0)
            {
                currentButton.innerHTML = "<";
                currentButton.id = "previous_button";
                currentButton.setAttribute("option_value", "previous");
            }    
            else
            {
                currentButton.innerHTML = ">";
                currentButton.id = "next_button";
                currentButton.setAttribute("option_value", "next");
            }
            currentButton.style.width = (Math.floor((1 / (maxNumPaginationButtons + 2)) * 100)).toString() + pctChar;
            currentButton.style.height = "auto";
            currentButton.onclick = function(){ 
                    var mainDiv = getClearedMainDiv();
                    var optionVal = this.getAttribute("option_value");
                    var category = mainDiv.getAttribute("category");
                    var numberResourcesDisplayed = parseInt(mainDiv.getAttribute("number_of_resources_displayed"));
                    var currentPageNum = parseInt(mainDiv.getAttribute("current_page"));
                    
                    if(optionVal === "previous")
                    {
                        if(currentPageNum != 1)
                        {
                            mainDiv.setAttribute("current_page", currentPageNum - 1);
                            currentPageNum = currentPageNum - 1;
                        }
                        
                    }
                    else if (optionVal === "next")
                    {
                        var lastPageNum = Math.ceil(potentialAdUrlsObj[category].length / numberResourcesDisplayed);
                        if(currentPageNum < lastPageNum)
                        {
                            mainDiv.setAttribute("current_page", currentPageNum + 1);    
                            currentPageNum = currentPageNum + 1;
                        }
                    }

                    var startIndex = (currentPageNum - 1) * numberResourcesDisplayed;                    

                    displayResourcesFromCategory(potentialAdUrlsObj, category, startIndex=startIndex, numberResourcesDisplayed=numberResourcesDisplayed);

                    var selectedButtonDict = {"category_button_index": -1, "number_of_resources_displayed_button_index": -1, "page_number_button_index": -1};
                    updateAllButtonRows(selectedButtonDict, potentialAdUrlsObj, startIndex);                     


                    /*
                    if(optionVal === "previous")
                    {
                        if(currentPageNum != 1)
                        {
                            mainDiv.setAttribute("current_page", currentPageNum - 1);
                            currentPageNum = currentPageNum - 1;
                        }
                        
                    }
                    else if (optionVal === "next")
                    {
                        var lastPageNum = Math.ceil(potentialAdUrlsObj[category].length / numberResourcesDisplayed);
                        if(currentPageNum < lastPageNum)
                        {
                            mainDiv.setAttribute("current_page", currentPageNum + 1);    
                            currentPageNum = currentPageNum + 1;
                        }
                    }


                    
                    
                    ////Make sure the buttons are numbered correctly (if the selected button has a number > 6 it will moved close to the median)
                    var leftmostNum = 0;
                    var rightmostNum = 0;
                    var lastPageNum = Math.ceil(potentialAdUrlsObj[startingCategory].length / numberResourcesDisplayed);
                    var updateNumbers = false;
                    var selectedButtonIndex = 1;
                    if(currentPageNum > 6 && (currentPageNum + 4) <= lastPageNum)
                    {
                        updateNumbers = true;
                        leftmostNum = currentPageNum - 5;
                        rightMostNum = Math.min(currentPageNum + 4, lastPageNum);
                        selectedButtonIndex = (currentPageNum - leftmostNum);
                    }
                    else if(currentPageNum > 6 && (currentPageNum + 4) > lastPageNum)
                    {
                        updateNumbers = true;
                        leftmostNum = currentPageNum - 5 - (lastPageNum - currentPageNum);
                        rightMostNum = currentPageNum + 4 - (lastPageNum - currentPageNum);
                        selectedButtonIndex = (currentPageNum - leftmostNum);
                    }
                    else if(currentPageNum <= 6)
                    {
                        updateNumbers = true;
                        leftmostNum = 1;
                        rightMostNum = 10;
                        selectedButtonIndex = currentPageNum;
                    }
                    //Update the numbered buttons' values
                    var paginationButtonRow = document.getElementById("pagination_div");
                    if(updateNumbers)
                    {
                        for(var buttonIndex = 0; buttonIndex <= (rightMostNum - leftmostNum); buttonIndex++)
                        {
                            var currentButton = paginationButtonRow.children[buttonIndex + 1]; //Used + 1 to skip previous button
                            var updatedNumber = leftmostNum + buttonIndex;
                            currentButton.innerHTML = updatedNumber;
                            currentButton.setAttribute("option_value", updatedNumber);
                        }
                    }

                    //*/
                };
                if(i == 0)
                    prevButton = currentButton;
                else
                    nextButton = currentButton;
        }
        //// Add previous button
        paginationButtonRow.appendChild(prevButton);

        ///Create and add the numbered buttons
        for(var optionIndex = 0; optionIndex < maxNumPaginationButtons; optionIndex++)
        {
            var currentButton = document.createElement("button");
            paginationButtonRow.appendChild(currentButton);
            currentButton.type = "button";
            currentButton.innerHTML = leftmostNumber + optionIndex;
            currentButton.id = leftmostNumber + optionIndex;
            currentButton.setAttribute("option_value", leftmostNumber + optionIndex);
            currentButton.style.width = (Math.floor((1 / (maxNumPaginationButtons + 2)) * 100)).toString() + pctChar;
            currentButton.style.height = "auto";
            if(optionIndex >= numOptions)
            {
                currentButton.style.display = "none";
            }
            currentButton.onclick = function(){ 
                    var mainDiv = getClearedMainDiv();
                    var currentPageNum = parseInt(this.getAttribute("option_value"));
                    mainDiv.setAttribute("current_page", currentPageNum);
                    var numberResourcesDisplayed = parseInt(mainDiv.getAttribute("number_of_resources_displayed"));
                    var category = mainDiv.getAttribute("category");
                    
                    var startIndex = (currentPageNum - 1) * numberResourcesDisplayed;

                    displayResourcesFromCategory(potentialAdUrlsObj, category, startIndex=startIndex, numberResourcesDisplayed=numberResourcesDisplayed);                    

                    var selectedButtonDict = {"category_button_index": -1, "number_of_resources_displayed_button_index": -1, "page_number_button_index": -1};
                    updateAllButtonRows(selectedButtonDict, potentialAdUrlsObj, startIndex);                    

                    /*
                    ////Make sure the buttons are numbered correctly (if the selected button has a number > 6 it will moved close to the median)
                    var leftmostNum = 0;
                    var rightmostNum = 0;
                    var lastPageNum = Math.ceil(potentialAdUrlsObj[startingCategory].length / numberResourcesDisplayed);
                    var updateNumbers = false;
                    var selectedButtonIndex = 1;
                    if(currentPageNum > 6 && (currentPageNum + 4) <= lastPageNum)
                    {
                        updateNumbers = true;
                        leftmostNum = currentPageNum - 5;
                        rightMostNum = Math.min(currentPageNum + 4, lastPageNum);
                        selectedButtonIndex = (currentPageNum - leftmostNum) + 1;
                    }
                    else if(currentPageNum > 6 && (currentPageNum + 4) > lastPageNum)
                    {
                        updateNumbers = true;
                        leftmostNum = currentPageNum - 5 - (lastPageNum - currentPageNum);
                        rightMostNum = lastPageNum;
                        selectedButtonIndex = (currentPageNum - leftmostNum);
                    }
                    else if(currentPageNum <= 6)
                    {
                        updateNumbers = true;
                        leftmostNum = 1;
                        rightMostNum = 10;
                        selectedButtonIndex = currentPageNum;
                    }
                    //Update the numbered buttons' values
                    var paginationButtonRow = document.getElementById("pagination_div");
                    if(updateNumbers)
                    {
                        for(var buttonIndex = 0; buttonIndex <= (rightMostNum - leftmostNum); buttonIndex++)
                        {
                            var currentButton = paginationButtonRow.children[buttonIndex + 1]; //Used + 1 to skip previous button
                            var updatedNumber = leftmostNum + buttonIndex;
                            currentButton.innerHTML = updatedNumber;
                            currentButton.setAttribute("option_value", updatedNumber);
                        }
                    }
                    //*/
                };
        }   
        /// Add next button     
        paginationButtonRow.appendChild(nextButton);

        for(var i = 0; i < paginationButtonRow.children.length; i++)
        {
            paginationButtonRow.children[i].style.background = "gainsboro";
            paginationButtonRow.children[i].style.color = "black";
        }        

        //Add a description that states the total number of resources for this category
        var totalNumResourcesDiv = document.createElement("div");
        var totalNumResourcesText = document.createElement("p");
        totalNumResourcesText.id = "total_number_of_resources";
        totalNumResourcesText.innerHTML = (potentialAdUrlsObj[startingCategory].length).toString();
        if(startingCategory === "html")
        {
            totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Web Page Ads";
        }
        else if(startingCategory === "video")
        {
            totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Video Ads";
        }
        else if(startingCategory === "audio")
        {
            totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Audio Ads";
        }        
        else if(startingCategory === "image")
        {
            totalNumResourcesText.innerHTML = totalNumResourcesText.innerHTML + " Potential Image Ads";
        }        
        totalNumResourcesDiv.appendChild(totalNumResourcesText);
        totalNumResourcesText.style.fontSize = "175" + pctChar;
        totalNumResourcesDiv.style.textAlign = "center";
        totalNumResourcesDiv.style.width = "98" + pctChar;
        totalNumResourcesDiv.style.margin = "0";  
        totalNumResourcesText.style.margin = "0";
        document.body.appendChild(totalNumResourcesDiv);

        var mainDiv = document.createElement("div");
        mainDiv.id = "main_div";
        document.body.appendChild(mainDiv)
        mainDiv.style.width = "100" + pctChar;
        mainDiv.style.margin = 0;
        mainDiv.style.padding = "0px";
        mainDiv.style.height = "auto";   
        mainDiv.setAttribute("category", categoryList[0]);
        mainDiv.setAttribute("number_of_resources_displayed", numResourcesOptionsList[0]);     
        mainDiv.setAttribute("start_index", 0);
        mainDiv.setAttribute("current_page", 1);

        categoryButtonRow.children[0].style.background = "darkgreen";
        categoryButtonRow.children[0].style.color = "white";

        numResourcesButtonRow.children[1].style.background = "darkgreen";
        numResourcesButtonRow.children[1].style.color = "white";

        paginationButtonRow.children[1].style.background = "darkgreen";
        paginationButtonRow.children[1].style.color = "white";
        
        

        displayResourcesFromCategory(potentialAdUrlsObj, categoryList[0], startIndex=0, numberResourcesDisplayed=parseInt(numResourcesOptionsList[0]));
    }

    initialSetup(potentialAdUrlsObj, categoryList, numResourcesOptionsList);
    """%(str(potentialAdUrlsDict), str(adContentList), str(ts), "%")
    driver.execute_script(displayPotentialAdsScript)
    # Remove the temporary directory that was created
    try:
        tempCollectionDict = os.path.abspath(os.getcwd()) + "/collections/" + "my-web-archive-" + str(ts)
        time.sleep(60*60*24)
    except KeyboardInterrupt:
        # Deleting the temporary directory that was created
        if os.path.exists(tempCollectionDict):
            try:
                shutil.rmtree(tempCollectionDict)
            except:
                print("Temporary Collection Was Not Deleted")                         
    finally:
        driver.close()
        pywbProcess.kill()
    



# main
if __name__ == "__main__":
    defaultValuesDict = {"replay_web_page_port_number": "8090", "replay_web_page_version": "1.5.11", "replay_web_page_embed_type": "replayonly", "python_version": "python3"}
    settings = [] 

    warcFilePath = sys.argv[1]
    containingWebpage = sys.argv[2].lower()
    adContentList = ["html", "video", "audio", "image"]
    filteredKeywordList = ["track", "safeframe.googlesyndication.com", "favicon", "pixel.gif", "pixel?", "/pixel.", "pixelframe", "usersync", "user_sync", "usync."]
    uniqueFilteredContentTypes = []
    uniqueAllowedContentTypes = []
    urlsWithoutAContentType = []
    potentialAdUrlsDict = {}
    initAdContentTypes(potentialAdUrlsDict, adContentList)
    with open(warcFilePath, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == 'response' and record.http_headers.get_header('Content-Type') != None:
                currentContentTypeSplit = record.http_headers.get_header('Content-Type').lower().split(";")[0].split("/")
                if len(currentContentTypeSplit) >= 2 and (currentContentTypeSplit[0] in adContentList or currentContentTypeSplit[1] in adContentList):
                    #print(record.rec_headers)
                    #print(record.http_headers.get_header('Content-Type'))
                    if record.http_headers.get_header('Content-Type').lower() not in uniqueAllowedContentTypes:
                        uniqueAllowedContentTypes.append(record.http_headers.get_header('Content-Type').lower())
                    
                    currentURL = record.rec_headers.get_header('WARC-Target-URI').lower()
                    if surt(currentURL) != surt(containingWebpage):
                        addToList = True
                        for filteredKeyword in filteredKeywordList:
                            if filteredKeyword in currentURL:
                                addToList = False
                                break
                        if addToList:
                            addURLToAdList(potentialAdUrlsDict, currentURL, currentContentTypeSplit, adContentList, warcFilePath, settings, defaultValuesDict)
                else:
                    #print(contentTypeList)
                    if record.http_headers.get_header('Content-Type').lower() not in uniqueFilteredContentTypes:
                        uniqueFilteredContentTypes.append(record.http_headers.get_header('Content-Type').lower())
                        #print("Content type not listed: " + record.http_headers.get_header('Content-Type'))
            elif record.rec_type == 'response':
                #print("Does not have a content type: " + record.rec_headers.get_header('WARC-Target-URI'))
                urlsWithoutAContentType.append(record.rec_headers.get_header('WARC-Target-URI'))
            '''
            if record.rec_headers.get_header('WARC-Target-URI') != None and record.rec_headers.get_header('WARC-Target-URI').lower() == uriR.lower():
                #print(record.rec_headers.get_header('WARC-Target-URI'))
                #print(record.rec_headers)
                #print(record.http_headers)
                #print(record.content_stream().read())
            '''

    #printAllowedContentTypes(uniqueAllowedContentTypes)
    #printFilteredContentTypes(uniqueFilteredContentTypes)
    #printUrlsWithoutAContentType(urlsWithoutAContentType)

    #printPotentialAdUrls(potentialAdUrlsDict)
    displayPotentialAds(potentialAdUrlsDict, settings, defaultValuesDict, warcFilePath, adContentList)
