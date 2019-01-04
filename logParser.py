#!/usr/bin/env python

from __future__ import print_function

import sys
import re
import os
import time
import json

# NOTE to self: Python     -> JSON
#               dict       -> Obj
#               list,tuple -> array
#               None       -> Null
# All other primitive vars are essentially 1:1


class LogParser:

  def __init__(self):
    # Initilize values needed for each log that need to be obtained while 
    self.logFileId = "none"
    self.logFileCycleId = "none"
    self.ota = "none"
    self.piQVersion = "none"
    self.oemFlavor = "none"
    self.deviceFlavor = "none"
    self.ticket = "none"

    self.logSummaries = []
    self.logEntries = []

    # regex to use for now:
    self.regDateTime = "\\d\\d-\\d\\d\\s(\\d\\d:){2}\\d\\d.\\d{3}"
    self.regLogLevel = "\\s[DIWEF]\\s"
    self.regPID_TID = "\\d+\\s+\\d+"
    self.regTag = "\\S+\\s*:"

    self.regOTA = "Firmware Version\\s*:\\s+\\d+.\\d+.\\d+.\\d+.\\d+"
    self.regPiQVersion = "Precision-IQ version\\s*:\\s+\\d+.\\d+.\\d+.\\d+.\\d+-\\w+-\\w+"
    self.regOemFlavor = "Precision-IQ flavor oem\\s*:\\s+\\w+"
    self.regDeviceFalvor = "Precision-IQ flavor device\\s*:\\s+\\w+"

  # Adds a summry to the summaryList
  # This will also make sure to check if the current summary should be a part of the previous logSummary
  def addSummary(self,lineNumber,dateTime,logLevel,pid_tid,tag,log):

    # an empty list returns False - thought it will otherwise return the list...
    logSummaryEmpty = True if not self.logSummaries else False

    # Make the new summary
    currSummary = {
      "lineNumber":lineNumber,
      "dateTime":dateTime,
      "logLevel":logLevel,
      "pid_tid":pid_tid,
      "tag":tag,
      "log":log
    }

    # TODO # I could likely clean up this logic here ...
    if logSummaryEmpty:
      self.logSummaries.append(currSummary)
    else:
      # Check that the current is not a part of the previous
      previousSummary = self.logSummaries[-1]
      isDateSame = previousSummary["dateTime"] == dateTime
      isPidSame = previousSummary["pid_tid"] == pid_tid
      isTagSame = previousSummary["tag"] == tag
      isLevelSame = previousSummary["logLevel"] == logLevel

      if isDateSame and isPidSame and isTagSame and isLevelSame:
        self.logSummaries[-1]["log"] += "\n"+log
      else:
        self.logSummaries.append(currSummary)

  def addEntry(self,summary):
    entry = {
      "logId":self.logFileId,
      "logCycle":self.logFileCycleId,
      "ota":self.ota,
      "piQVersion":self.piQVersion,
      "oemFlavor":self.oemFlavor,
      "deviceFlavor":self.deviceFlavor,
      "ticket":self.ticket,
      "summary":summary
    }
    self.logEntries.append(entry)

  # Take a line to parse, a regex term to use, and return the term found, and the rest of the line
  def consumeSearch(self,line,regex):
    lineSearch = re.search(regex,line)
    if lineSearch != None:
      term = lineSearch.group().strip()
      line = line[lineSearch.end():]
      return (term,line)
    else:
      return ("none",line)

  def parseLine(self,line,lineNumber):
    # initilize:
    pid_tid = "none"
    logLevel = "none"
    dateTime = "none"
    tag = "none"

    # Check for OTA, VersionNumber, oem and device before consuming the line being parsed
    self.ota = self.checkForExtra(line,self.regOTA,self.ota)
    self.piQVersion = self.checkForExtra(line,self.regPiQVersion,self.piQVersion)
    self.oemFlavor = self.checkForExtra(line,self.regOemFlavor,self.oemFlavor)
    self.deviceFlavor = self.checkForExtra(line,self.regDeviceFalvor,self.deviceFlavor)

    dateTime, line = self.consumeSearch(line,self.regDateTime)
    pid_tid, line = self.consumeSearch(line,self.regPID_TID)
    logLevel, line = self.consumeSearch(line,self.regLogLevel)
    tag, line = self.consumeSearch(line,self.regTag)    

    self.addSummary(lineNumber,dateTime,logLevel,pid_tid,tag,line.strip())

# I Moved this all to addSummary - so this could be removed. Leaving it encase I broke something
#    # If logSummaries is empty
#    if not self.logSummaries:
#      self.addSummary(lineNumber,dateTime,logLevel,pid_tid,tag,line.strip())
#
#    else:
#      previousLog = self.logSummaries[-1]
#      isDateSame = previousLog["dateTime"] == dateTime
#      isPidSame = previousLog["pid_tid"] == pid_tid
#      isTagSame = previousLog["tag"] == tag
#      isLevelSame = previousLog["logLevel"] == logLevel
#
#      # Check if current log should be added to previous
#      if isDateSame and isPidSame and isTagSame and isLevelSame:
#        self.logSummaries[-1]["log"] += "\n"+line.strip()
#      else:
#        self.addSummary(lineNumber,dateTime,logLevel,pid_tid,tag,line.strip())

  # While parsing I need to look for OTA, VersionNumber, OEM and Device
  def checkForExtra(self,line,regex,extra):
    lineSearch = re.search(regex,line)
    if extra == "none" and lineSearch != None:
      return lineSearch.group()
    else:
      return extra

  def hasAllExtras(self):
    hasOTA = True if self.ota != "none" else False
    hasVersion = True if self.piQVersion != "none" else False
    hasOEM = True if self.oemFlavor != "none" else False
    hasDevice = True if self.deviceFlavor != "none" else False

    return (hasOTA and hasVersion and hasOEM and hasDevice)

  def readLog(self,logFile):
    i = 1
    file = open(logFile) 
    for line in file.readlines():
      self.parseLine(line,i)
      i+=1
    file.close


def main():
  parser = LogParser()
  parser.readLog(sys.argv[1])

  # If I make logSummaries a buffered reader - I could run this all in parallel
  # and then have the addEntry instead write to the database in aync
  for summary in parser.logSummaries:
    parser.addEntry(summary)

  # This is just for a visual to make sure it is working
  for entry in parser.logEntries:
    if entry["summary"]["logLevel"] == "F":
      print(json.dumps(entry,indent=2,sort_keys=True))

if __name__ == "__main__":
  main()
