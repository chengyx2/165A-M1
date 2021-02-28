from template.config import *
from template.page import PageRange
import pickle
"""
BufferPageRange is a page range that stays on BufferPool.
"""
class BufferPageRange:

    def __init__(self):
        self.pageRange_Index = None
        self.pageRange = None
        self.pin = 0
        self.dirty = 0
    
    def isEmpty(self):
        return self.pageRange_Index == None

    def isDirty(self):
        return self.dirty == 1
    
    # Check if there is no transcation on this page range.
    def isAvailable(self):
        return self.pin == 0
    
    def readFromFile(self):
        with open('pagerange%d' %self.pageRange_Index, 'rb') as file:
            self.pageRange = pickle.load(file)
        self.dirty = 0
        return True

    def writeToFile(self):
        with open('pagerange%d' %self.pageRange_Index, 'wb') as file:
            pickle.dump(self.pageRange, file, pickle.HIGHEST_PROTOCOL)
        self.dirty = 0
        return True

    def clear(self):
        self.pageRange_Index = None
        self.pageRange = None
        self.pin = 0
        self.dirty = 0
        return True
    

"""
BufferPool is a container that holds several BufferPageRanges
"""

class BufferPool:

    def __init__(self, num_columns):
        self.pageRanges = [BufferPageRange()] * BUFFER_POOL_SIZE
        self.num_columns = num_columns
        self.pageRanges[0].pageRange_Index = 0
        self.pageRanges[0].pageRange = PageRange(self.num_columns)

    def findPageRange(self, pageRange_index):
        for Index in range(0, BUFFER_POOL_SIZE):
            if self.pageRanges[Index].pageRange_Index == pageRange_index:
                return self.pageRanges[Index]
        return False
    
    def findEmptyPage(self):
        return self.findPageRange(None)
    
    # Get the requested page range from buffer pool or load from file if not exists in bufferpool
    def getPageRange(self, pageRange_index):
        if not self.findPageRange(pageRange_index):
            return self.load(pageRange_index)
        else:
            return self.findPageRange(pageRange_index)

    # Get an empty page range or evict a page range if buffer pool is full
    def getEmptyPage(self):
        if not self.findEmptyPage():
            return self.evict()
        else:
            return self.findEmptyPage()
    
    # Flush all dirty page ranges before closing database
    def flushDirty(self):
        for pageRange in self.pageRanges:
            if pageRange.isDirty():
                pageRange.writeToFile()
        return True

    # Evict the least recently used page range(Could use MRU as well)
    def evict(self):
        if self.pageRange == None:
                print("Nothing to be evict")
                return False
        i = 0
        while True:
            item = self.pageRange[i]
            if item.isAvailable:
                if item.isDirty:
                    item.writeToFile()
                    self.pageRange.pop(i)
                    break
                else:
                    self.pageRange.pop(i)
                pageRange.clear()
                return True
            else:
                i += 1 
                item = self.pageRange[i]
        return True
    # Load the wanted page range onto buffer pool
    def load(self, pageRange_index):
        emptyPageRange = self.getEmptyPage()
        emptyPageRange.pageRange_Index = pageRange_index
        emptyPageRange.readFromFile()
        loadedPageRange = emptyPageRange
        return loadedPageRange

    # +++ member functions in table class, similar here?
