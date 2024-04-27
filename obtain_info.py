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
    __INF_BAG_WEIGHT= 23
    __FOREIGN_GOLD_FLYER_BAG_WEIGHT = 23

    def __init__(self,PrContent):
        #print('CPAX initialized. ___________________________')
        if not isinstance(PrContent,str):
            print("PrContent is not a string type.")
            return
    
    def run(self,PrContent):
        #try:
            #Initialize all variables in class level.
            self.debug_msg.clear()
            self.debug_msg.append('---------------------------------')
            self.error_msg.clear()
            self.BoardingNumber = 0
            self.PrPdNumber = 0
            self.__ChkBagAverageWeight = 0
            self.__ChkBagPcs = 0
            self.__Pr=PrContent
            #Call methods.
            bolRun = True
            bolRun = self.__GetBnAndCls()
            if bolRun:
                self.__GetChkBag()
                self.__MatchingBag()
                #self.__GetPassportExp(PrContent)
                #self.__NameMatch(PrContent)
        #except:
        #    self.error_msg.append("A Fatal Error occured at PR" + str(self.PrPdNumber)+"PD; Boarding Number should be "+str(self.BoardingNumber))

    def __del__(self):
        self.debug_msg.append("Boarding number"+ str(self.BoardingNumber) +". \nCPax deconstruction.")
    
    def __GetBnAndCls(self):
        bnPat = re.compile(r'BN\d{3}(\s{2}|\s\*)(\d|U)')#Pax may be onboard.
        bnMatch = bnPat.search(self.__Pr)
        if bnMatch == None:
            self.BoardingNumber = self.__ERROR_NUMBER
        else:
            bnIndex = bnMatch.start() + 2
            self.BoardingNumber = int(self.__Pr[bnIndex:bnIndex + 3])
        self.debug_msg.append("boarding # = "+str(self.BoardingNumber))

        clsPat = re.compile(r'\s{2}[A-Z]\s{1}')
        clsIndex = clsPat.search(self.__Pr,bnIndex,bnIndex + 20).start() + 2
        self.__MainCls = self.__Pr[clsIndex]
        fltArgs = CArgs()
        self.__MainCls = fltArgs.SubCls2MainCls(self.__MainCls)
        self.debug_msg.append("main class = "+self.__MainCls)

        pdPat = re.compile(r',\d{1,3}PD\s{1}')
        pdMatch = pdPat.search(self.__Pr)
        if pdMatch == None:#Limit just for PD pax.
            self.PrPdNumber = self.__ERROR_NUMBER
        else:
            pdIndexS = pdMatch.start() + 1
            pdIndexE = pdMatch.end() - 3
            self.PrPdNumber = int(self.__Pr[pdIndexS:pdIndexE])
        self.debug_msg.append("pd sequnce = "+str(self.PrPdNumber))

        return True
    #__GetBnAndCls() end.
    
    def __GetChkBag(self):
        indexE = 1
        bagCount = 0
        bagWeight = 0
        bagPat = re.compile(r'BAG\d{1}/\d{1,3}/')
        bagMatch = bagPat.search(self.__Pr,indexE)
        if bagMatch:
            indexS = bagMatch.start() + 3
            indexE = bagMatch.end() - 1
            bagCount = bagCount + int(self.__Pr[indexS:indexS + 1])
            bagWeight = bagWeight + int(self.__Pr[indexS + 2:indexE])
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

    #Return type map.
    #['piece','weight']
    def __ExpcStatement(self):
        pat=re.compile(r'EXPC-\s')
        re_match=pat.search(self.__Pr)
        result={}
        if re_match == None:
            return result
        #insert expc amount.
        try:
            result['piece']=int(self.__Pr[re_match.end()])
        except:
            self.debug_msg.append("expc piece type error.")

        w_total=0
        end_index=1
        pat=re.compile(r'/\d{2}KG-')
        while True:
            re_match=pat.search(self.__Pr,end_index)
            if re_match==None:
                break
            w = self.__Pr[re_match.start()+1:re_match.start()+3]
            try:
                w_int = int(w)
            except:
                self.debug_msg.append("expc ttl w type error.")
            w_total = w_total + w_int
            end_index=re_match.end()
        #insert expc total weight.
        result['weight']=w_total

        self.debug_msg.append("expc piece = " + str(result['piece']))
        self.debug_msg.append("expc ttl w = " + str(result['weight']))
        return result
    #__ExpcStatement() end.

    #Return type map.
    #['index','piece']
    def __AsvcBagStatement(self,StartIndex=1):
        pat=re.compile(r'ASVC-\s')
        re_match=pat.search(self.__Pr,StartIndex)
        result={}
        if re_match == None:
            return result
        else:
            result['index']=re_match.end()
            result['piece']=0
        pat=re.compile(r'XBAG/')
        re_match=pat.search(self.__Pr,result['index'])
        if re_match:
            return result
        pat=re.compile(r'/\dPC')
        re_match=pat.search(self.__Pr,result['index'])
        if re_match:
            try:
                result['piece'](int(self.__Pr[re_match.start()+1]))
                result['index']=re_match.end()
                self.debug_msg.append("asvc bag p = " + str(result['piece']))
            except:
                self.debug_msg.append("asvc bag p type error")

        return result
    #__AsvcBagStatement() end.

    #return a map type.
    #['FBA','IFBA']
    def __RegularBags(self):
        pat=re.compile(r'\sFBA/\dPC')
        re_match=pat.search(self.__Pr)
        result={'FBA':2,'IFBA':0}
        if re_match:
            try:
                result['FBA']=int(self.__Pr[re_match.start() + 5])
            except:
                self.error_msg.append("FBA got an error. Set default as 2 pieces.")
        pat=re.compile(r'\sIFBA/\dPC')
        re_match=pat.search(self.__Pr)
        if re_match:
            result['IFBA']=1

        self.debug_msg.append("adult bag  = " + str(result['FBA']))
        self.debug_msg.append("Infant bag = " + str(result['IFBA']))
        return result
    #__RegularBags() end.
    
    #return a map.
    #key['piece','bol_ca']
    def __FlyerBenifit(self):
        pat=re.compile(r'\sFF/.')
        re_match=pat.search(self.__Pr)
        #默认没有会员，也不是国航常旅客
        result={'piece':0,"bol_ca":False}
        if re_match:
            if self.__Pr[re_match.end():re_match.end()+1]=='CA':
                result["bol_ca"]=True
        else:
            return result
        pat=re.compile(r'/\*G\s')
        re_match=pat.search(self.__Pr)
        #如果是金卡，都有会员优惠。
        if re_match:
            result["piece"]=1
        pat=re.compile(r'/\*S\s')
        re_match=pat.search(self.__Pr)
        #如果是银卡的国航会员，才有优惠。
        if re_match and result['bol_ca']:
            result["piece"]=1
        
        self.debug_msg.append("flyer benif = " + str(result["piece"]))
        self.debug_msg.append("CA flyer    = " + str(result["bol_ca"]))
        return result
    #__FlyerBenifit() end.

    # return a map.
    # ['piece', 'weight']
    def __CalculateBagPieceAndWeight(self):
        expc=self.__ExpcStatement()
        index=1
        asvc_tmp={}
        asvc=0 # Because the asvc result needs to accumulate.
        result={'piece':0,'weight':0}
        arg=CArgs()
        while True:
            asvc_tmp=self.__AsvcBagStatement(index)
            if len(asvc_tmp) == 0:
                break
            else:
                index=asvc_tmp['index']
                asvc=asvc+asvc_tmp['piece']
        if expc:
            result['piece']=expc['piece']+asvc
            result['weight']=expc['weight']+asvc*arg.ClassBagWeight(self.__MainCls)
            self.debug_msg.append("total piece = " + str(result['piece']))
            self.debug_msg.append("total weigh = " + str(result['weight']))

            return result

        regular=self.__RegularBags()
        flyer=self.__FlyerBenifit()
        #总件数=常旅客+网购+成人票+婴儿票
        result['piece']=flyer['piece']+asvc+regular['FBA']+regular['IFBA']
        if flyer['bol_ca']:
            #总重量 =（CA常旅客+网购+成人票） x 舱位重量
            result['weight']=( flyer['piece']+asvc+regular['FBA'] ) * arg.ClassBagWeight(self.__MainCls)
        else:
            #总重量 = （非CA常旅客 x 金卡限制）+ （网购+成人票）x 舱位重量
            result['weight']=flyer['piece']*self.__FOREIGN_GOLD_FLYER_BAG_WEIGHT + ( asvc+regular['FBA'] ) * arg.ClassBagWeight(self.__MainCls)
        if regular['IFBA']!=0:
                #总重量 附加 婴儿票重量。
                result['weight']=result['weight']+self.__INF_BAG_WEIGHT
        self.debug_msg.append("total piece = " + str(result['piece']))
        self.debug_msg.append("total weigh = " + str(result['weight']))
        return result
    # __CalulateBagPieceAndWeight() end.

    def __MatchingBag(self):
        max_bag=self.__CalculateBagPieceAndWeight()
        if self.__ChkBagPcs > max_bag['piece']:
            self.error_msg.append("PR"+str(self.PrPdNumber)+"PD,BN#"+str(self.BoardingNumber)+" has many bags.")
        if self.__ChkBagTtlWeight > max_bag['weight']:
            self.error_msg.append("PR"+str(self.PrPdNumber)+"PD,BN#"+str(self.BoardingNumber)+" baggage is overweight.")
        return