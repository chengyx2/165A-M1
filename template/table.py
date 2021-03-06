from template.page import PageRange
from template.index import Index
from template.config import *
from template.bufferpool import BufferPool
from time import time
import queue

'''
The Table class provides the core of our relational storage functionality. All columns are
64-bit integers in this implementation. Users mainly interact with tables through queries.
Tables provide a logical view over the actual physically stored data and mostly manage
the storage and retrieval of data. Each table is responsible for managing its pages and
requires an internal page directory that given a RID it returns the actual physical location
of the record. The table class should also manage the periodical merge of its
corresponding page ranges.
'''

class Record:

    def __init__(self, rid, key, columns):
        self.rid = rid
        self.key = key
        self.columns = columns

    def getColumns(self):
        return self.columns

class Table:

    """
    :param name: string         #Table name
    :param num_columns: int     #Number of Columns: all columns are integer
    :param key: int             #Index of table key in columns
    """
    def __init__(self, name, num_columns, key):
        self.name = name
        self.key = key
        self.num_columns = num_columns
        self.bufferpool = BufferPool(self.num_columns)
        #self.page_directory = {}
        self.tailPage_lib = {} # Store tailRID: tailLocation, so that we can find a tail record
        self.index = Index(self)
        self.num_PageRanges = 1

        # baseRID and tailRID are initialized to 1, 0 is for deleted record
        self.baseRID = 1
        self.tailRID = 1

        #merge
        self.mergeQ = queue.Queue()
        self.deallocateQ = queue.Queue()
        '''
        # Unused bit vector definition for RID(May be used in M2 M3):
        # RID is a list of integer storing relevant info about a record(location, deleted)
        # Store RID in page ---> Use 8 bytes where the first 4 bytes are used to define the location of a record:
        # 1 byte for pageRange_index, 1 byte for pageList_index, 1 byte for offset_index, 
        # 1 byte for deleted or not(not deleted:0 deleted:1)
        '''

    def create_NewPageRange(self):
        emptyPageRange = self.bufferpool.getEmptyPage()
        emptyPageRange.pageRange_Index = self.num_PageRanges
        emptyPageRange.pageRange = PageRange(self.num_columns)
        self.num_PageRanges += 1
        return True
        
    # Find the locaion of a base record, location is a list of indices locating a base record
    def baseRIDToLocation(self, baseRID):
        pageRange_index = (baseRID - 1) // (MAX_NUM_RECORD * BASE_PAGE_PER_PAGE_RANGE)
        basePageList_index = (baseRID - 1 - MAX_NUM_RECORD * BASE_PAGE_PER_PAGE_RANGE * pageRange_index) // MAX_NUM_RECORD
        offset_index = baseRID - MAX_NUM_RECORD * (BASE_PAGE_PER_PAGE_RANGE * pageRange_index+basePageList_index) - 1
        location = [pageRange_index, basePageList_index, offset_index]
        return location

    # Given a baseRID return a list of values in base record
    # The way to access a value using a location: 
    # e.g. value = int.from_bytes(pageRanges[pageRange_index].basePageList
    # [basePageList_index].colPages[columnNum].data[offset_index*INT_SIZE:(offset_index+1)*INT_SIZE], 'big')
    def baseRIDToRecord(self, baseRID):
        location = self.baseRIDToLocation(baseRID)
        pageRange_index = location[0]
        basePageList_index = location[1]
        offset_index = location[2]
        
        bufferPageRange = self.bufferpool.getPageRange(pageRange_index)
        baseRecord = []
        for i in range(INTERNAL_COL_NUM+self.num_columns):
            baseRecord.append(int.from_bytes(bufferPageRange.pageRange.basePageList[basePageList_index].colPages[i].data \
                [offset_index*INT_SIZE:(offset_index+1)*INT_SIZE], 'big'))
            
        return baseRecord
    
    # Given a tailRID return a list of values in tail record
    def tailRIDToRecord(self, tailRID):
        location = self.tailPage_lib[tailRID]
        pageRange_index = location[0]
        tailPageList_index = location[1]
        offset_index = location[2]

        bufferPageRange = self.bufferpool.getPageRange(pageRange_index)
        tailRecord = []
        for i in range(INTERNAL_COL_NUM+self.num_columns):
            tailRecord.append(int.from_bytes(bufferPageRange.pageRange.tailPageList[tailPageList_index].colPages[i].data \
                [offset_index*INT_SIZE:(offset_index+1)*INT_SIZE], 'big'))
        return tailRecord
    
    # Overwrite a value in base record
    def baseWriteByte(self, value, baseRID, columnNum):
        location = self.baseRIDToLocation(baseRID)
        pageRange_index = location[0]
        basePageList_index = location[1]
        offset_index = location[2]

        bufferPageRange = self.bufferpool.getPageRange(pageRange_index)
        bufferPageRange.pageRange.basePageList[basePageList_index] \
            .colPages[columnNum].data[offset_index*INT_SIZE:(offset_index+1)*INT_SIZE] = \
                value.to_bytes(INT_SIZE, 'big')
        return True

    # Overwrite a value in tail record
    def tailWriteByte(self, value, tailRID, columnNum):
        location = self.tailPage_lib[tailRID]
        pageRange_index = location[0]
        tailPageList_index = location[1]
        offset_index = location[2]

        bufferPageRange = self.bufferpool.getPageRange(pageRange_index)
        bufferPageRange.pageRange.tailPageList[tailPageList_index] \
            .colPages[columnNum].data[offset_index*INT_SIZE:(offset_index+1)*INT_SIZE] = \
                value.to_bytes(INT_SIZE, 'big')
        return True

    # Commit available associated tail page
    def commitTailPage(self):
        for pageRange_index in range(self.num_PageRanges):
            bufferPageRange = self.bufferpool.getPageRange(pageRange_index)
            if bufferPageRange.isAvailable():
                for basePage_index in range(len(bufferPageRange.pageRange.basePageList)):
                    associatedTailPage = {}
                    for baseRID in range(basePage_index*512+1+16*512*pageRange_index, \
                        (basePage_index+1)*512+1+16*512*pageRange_index):
                        baseRecord = self.baseRIDToRecord(baseRID)
                        if tailRID != 0:
                            tailRID = baseRecord[INDIRECTION_COLUMN]
                            tailRecord = self.tailRIDToRecord(tailRID)
                            associatedTailPage[baseRID] = tailRecord
                    self.mergeQ.put(associatedTailPage)

    def merge(self):
        while True:
            if not self.mergeQ.empty():
                associatedTailPage = mergeQ.get()
                mergedBasePage = 
