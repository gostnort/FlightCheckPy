import re
import collections
import datetime
from general_func import CArgs

class CPax():
    """This class will process a single passenger information from PR page."""

    #Output variables.
    error_msg = []
    BoardingNumber = 0
    PrPdNumber = 0
    debug_msg=[]

    #Private variables.
    __ChkBagAverageWeight = 0
    __ChkBagPcs = 0
    __ChkBagTtlWeight = 0
    __MainCls = ""
    __ERROR_NUMBER = 65535

    def __init__(self,PrContent):
        if not isinstance(PrContent,str):
            print("PrContent is not a string type.")
            return
        self.debug_msg.clear()
        self.debug_msg.append("CPax initialized.___________________________________")
        #Initialize all variables in class level.
        self.error_msg.clear()
        self.BoardingNumber = 0
        self.PrPdNumber = 0
        self.__ChkBagAverageWeight = 0
        self.__ChkBagPcs = 0
        #Call methods.
        bolRun = True
        bolRun = self.__GetBnAndCls(PrContent)
        if bolRun:
            self.__ExpcStatement(PrContent)
            self.__GetChkBag(PrContent)
            #self.__CalculateBag(PrContent)
            #self.__GetPassportExp(PrContent)
            #self.__NameMatch(PrContent)

    def __del__(self):
        self.debug_msg.append("Boarding number"+ str(self.BoardingNumber) +". \nCPax deconstruction.")
    
    def __GetBnAndCls(self,PrContent):
        bnPat = re.compile(r'BN\d{3}(\s{2}|\s\*)(\d|U)')#Pax may be onboard.
        bnMatch = bnPat.search(PrContent)
        if bnMatch == None:
            self.BoardingNumber = self.__ERROR_NUMBER
        else:
            bnIndex = bnMatch.start() + 2
            self.BoardingNumber = int(PrContent[bnIndex:bnIndex + 3])
        self.debug_msg.append("boarding # = "+str(self.BoardingNumber))

        clsPat = re.compile(r'\s{2}[A-Z]\s{1}')
        clsIndex = clsPat.search(PrContent,bnIndex,bnIndex + 20).start() + 2
        self.__MainCls = PrContent[clsIndex]
        fltArgs = CArgs()
        self.__MainCls = fltArgs.SubCls2MainCls(self.__MainCls)
        self.debug_msg.append("main class = "+self.__MainCls)

        pdPat = re.compile(r',\d{1,3}PD\s{1}')
        pdMatch = pdPat.search(PrContent)
        if pdMatch == None:#Limit just for PD pax.
            self.PrPdNumber = self.__ERROR_NUMBER
        else:
            pdIndexS = pdMatch.start() + 1
            pdIndexE = pdMatch.end() - 3
            self.PrPdNumber = int(PrContent[pdIndexS:pdIndexE])
        self.debug_msg.append("pd sequnce = "+str(self.PrPdNumber))

        return True
    #__GetBnAndCls() end.
    
    def __GetChkBag(self,PrContent):
        indexE = 1
        bagCount = 0
        bagWeight = 0
        bagPat = re.compile(r'BAG\d{1}/\d{1,3}/')
        bagMatch = bagPat.search(PrContent,indexE)
        if bagMatch:
            indexS = bagMatch.start() + 3
            indexE = bagMatch.end() - 1
            bagCount = bagCount + int(PrContent[indexS:indexS + 1])
            bagWeight = bagWeight + int(PrContent[indexS + 2:indexE])
        if bagCount == 0:
            self.__ChkBagAverageWeight = 0
        else:
            self.__ChkBagAverageWeight = bagWeight / bagCount
        self.__ChkBagPcs = bagCount
        self.__ChkBagTtlWeight = bagWeight

        self.debug_msg.append("bag piece  = " + str(self.__ChkBagPcs))
        self.debug_msg.append("bag total w= " + str(self.__ChkBagTtlWeight))
        self.debug_msg.append("bag averag = " + str(self.__ChkBagAverageWeight))
    #__GetChkBag() end.

    #Return type List.
    def __ExpcStatement(self,PrContent):
        pat=re.compile(r'EXPC-\s')
        re_match=pat.search(PrContent)
        result=[]
        if re_match == None:
            return result
        #insert expc amount.
        result.append(PrContent[re_match.end()])

        w_total=0
        end_index=1
        pat=re.compile(r'/\d{2}KG-')
        while True:
            re_match=pat.search(PrContent,end_index)
            if re_match==None:
                break
            w = PrContent[re_match.start()+1:re_match.start()+3]
            try:
                w_int = int(w)
            except:
                self.debug_msg.append("expc ttl w type error.")
            w_total = w_total + w_int
            end_index=re_match.end()
        #insert expc total weight.
        result.append(w_total)

        self.debug_msg.append("expc piece = " + str(result[0]))
        self.debug_msg.append("expc ttl w = " + str(result[1]))
        return result
    #__ExpcStatement() end.

    #Return type Int.
    def __AsvcBagStatement(self,PrContent,StartIndex=1):
        pat=re.compile(r'ASVC-\s')
        re_match=pat.search(PrContent,StartIndex)
        result=0
        if re_match == None:
            return result
        else:
            StartIndex=re_match.end()
        pat=re.compile(r'XBAG/')
        re_match=pat.search(PrContent,StartIndex)
        if re_match:
            return result
        else:
            StartIndex=re_match.end()
        pat=re.compile(r'\dPC')
        re_match=pat.search(PrContent,StartIndex)
        if re_match:
            try:
                result = int(PrContent[re_match.start()])
            except:
                self.debug_msg.append("asvc bag p type error")

        self.debug_msg.append("asvc bag p = " + str(result))
        return result
    #__AsvcBagStatement() end.