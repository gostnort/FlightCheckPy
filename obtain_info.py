import re
import datetime
from general_func import CArgs


class CPax:
    """This class will process a single passenger information from PR page."""

    # Output variables.
    error_msg = []
    BoardingNumber = 0
    PrPdNumber = 0
    debug_msg = []

    # Private variables.
    __ChkBagAverageWeight = 0
    __ChkBagPcs = 0
    __ChkBagTtlWeight = 0
    __MainCls = ""
    __ERROR_NUMBER = 65535
    __INF_BAG_WEIGHT = 23
    __FOREIGN_GOLD_FLYER_BAG_WEIGHT = 23
    __SEPARATED_BAR = "__________________________________"
    __BolError = False

    def __init__(self, PrContent):
        if not isinstance(PrContent, str):
            print("PrContent is not a string type.")
            return

    def run(self, PrContent):
        try:
            # Initialize all variables in class level.
            self.debug_msg.clear()
            self.debug_msg.append(self.__SEPARATED_BAR)
            self.error_msg.clear()
            self.BoardingNumber = 0
            self.PrPdNumber = 0
            self.__ChkBagAverageWeight = 0
            self.__ChkBagPcs = 0
            self.__Pr = PrContent
            self.__BolError=False
            # Call methods.
            bolRun = True
            bolRun = self.__GetBnAndCls()
            if bolRun:
                self.__GetChkBag()
                self.__MatchingBag()
                self.__GetPassportExp()
                self.__NameMatch()
            #Even the functions are completed,
            #those '.clear()' may not finish yet. T~T
            if self.__BolError:
                self.error_msg.append('BN#' + str(self.BoardingNumber) + self.__SEPARATED_BAR + '\n')
        except:
            self.error_msg.append(
                "A Fatal Error occured at PR"
                + str(self.PrPdNumber)
                + "PD; Boarding Number should be "
                + str(self.BoardingNumber)
            )

    def __del__(self):
        self.debug_msg.append(
            "Boarding number" + str(self.BoardingNumber) + ". \nCPax deconstruction."
        )

    def __GetBnAndCls(self):
        # Search the boarding number.
        bnPat = re.compile(r"BN\d{3}(\s{2}|\s\*)(\d|U)")  # Pax may be onboard.
        bnMatch = bnPat.search(self.__Pr)
        if bnMatch:
            try:
                bnIndex = bnMatch.start() + 2
                self.BoardingNumber = int(self.__Pr[bnIndex : bnIndex + 3])
                self.debug_msg.append("boarding # = " + str(self.BoardingNumber))
            except:
                self.BoardingNumber = self.__ERROR_NUMBER
        # Search the sub-class to convert to main class.
        clsPat = re.compile(r"\s{2}[A-Z]\s{1}")
        try:
            clsIndex = clsPat.search(self.__Pr, bnIndex, bnIndex + 20).start() + 2
            self.__MainCls = self.__Pr[clsIndex]
        except:
            self.error_msg.append(
                "PR"
                + str(self.PrPdNumber)
                + "PD,\tNone validity classes are found."
            )
            self.__BolError=True
            return False
        fltArgs = CArgs()
        self.__MainCls = fltArgs.SubCls2MainCls(self.__MainCls)
        self.debug_msg.append("main class = " + self.__MainCls)
        # Search the PD sequnce number.
        pdPat = re.compile(r",\d{1,3}PD\s{1}")
        pdMatch = pdPat.search(self.__Pr)
        if pdMatch:  # Limit just for PD pax.
            try:
                pdIndexS = pdMatch.start() + 1
                pdIndexE = pdMatch.end() - 3
                self.PrPdNumber = int(self.__Pr[pdIndexS:pdIndexE])
                self.debug_msg.append("pd sequnce = " + str(self.PrPdNumber))
            except:
                self.PrPdNumber = self.__ERROR_NUMBER
        return True

    # __GetBnAndCls() end.

    def __GetChkBag(self):
        indexE = 1
        bagCount = 0
        bagWeight = 0
        bagPat = re.compile(r"BAG\d{1}/\d{1,3}/")
        bagMatch = bagPat.search(self.__Pr, indexE)
        if bagMatch:
            indexS = bagMatch.start() + 3
            indexE = bagMatch.end() - 1
            bagCount = bagCount + int(self.__Pr[indexS : indexS + 1])
            bagWeight = bagWeight + int(self.__Pr[indexS + 2 : indexE])
        if bagCount == 0:
            self.__ChkBagAverageWeight = 0
        else:
            self.__ChkBagAverageWeight = bagWeight / bagCount
        self.__ChkBagPcs = bagCount
        self.__ChkBagTtlWeight = bagWeight

        self.debug_msg.append("bag piece  = " + str(self.__ChkBagPcs))
        self.debug_msg.append("bag total w= " + str(self.__ChkBagTtlWeight))
        self.debug_msg.append("bag averag = " + str(self.__ChkBagAverageWeight))

    # __GetChkBag() end.

    # Return type map.
    # ['piece','weight']
    def __ExpcStatement(self):
        pat = re.compile(r"EXPC-\s")
        re_match = pat.search(self.__Pr)
        result = {}
        if re_match is None:
            return result
        # insert expc amount.
        try:
            result["piece"] = int(self.__Pr[re_match.end()])
        except ValueError:
            self.debug_msg.append("expc piece type error.")

        w_total = 0
        end_index = 1
        pat = re.compile(r"/\d{2}KG-")
        while True:
            re_match = pat.search(self.__Pr, end_index)
            if re_match is None:
                break
            w = self.__Pr[re_match.start() + 1 : re_match.start() + 3]
            try:
                w_int = int(w)
            except:
                self.debug_msg.append("expc ttl w type error.")
            w_total = w_total + w_int
            end_index = re_match.end()
        # insert expc total weight.
        result["weight"] = w_total

        self.debug_msg.append("expc piece = " + str(result["piece"]))
        self.debug_msg.append("expc ttl w = " + str(result["weight"]))
        return result

    # __ExpcStatement() end.

    # Return type map.
    # ['index','piece']
    def __AsvcBagStatement(self, StartIndex=1):
        pat = re.compile(r"ASVC-\s")
        re_match = pat.search(self.__Pr, StartIndex)
        result = {}
        if re_match is None:
            return result
        else:
            result["index"] = re_match.end()
            result["piece"] = 0
        pat = re.compile(r"XBAG/")
        re_match = pat.search(self.__Pr, result["index"])
        if re_match:
            return result
        pat = re.compile(r"/\dPC")
        re_match = pat.search(self.__Pr, result["index"])
        if re_match:
            try:
                result["piece"](int(self.__Pr[re_match.start() + 1]))
                result["index"] = re_match.end()
                self.debug_msg.append("asvc bag p = " + str(result["piece"]))
            except:
                self.debug_msg.append("asvc bag p type error")

        return result

    # __AsvcBagStatement() end.

    # return a map type.
    # ['FBA','IFBA']
    def __RegularBags(self):
        pat = re.compile(r"\sFBA/\dPC")
        re_match = pat.search(self.__Pr)
        result = {"FBA": 2, "IFBA": 0}
        if re_match:
            try:
                result["FBA"] = int(self.__Pr[re_match.start() + 5])
            except:
                self.error_msg.append(
                    "PR"
                    + str(self.PrPdNumber)
                    + "PD,\tFBA got an error. Set default as 2 pieces."
                )
                self.__BolError=True
        pat = re.compile(r"\sIFBA/\dPC")
        re_match = pat.search(self.__Pr)
        if re_match:
            result["IFBA"] = 1

        self.debug_msg.append("adult bag  = " + str(result["FBA"]))
        self.debug_msg.append("Infant bag = " + str(result["IFBA"]))
        return result

    # __RegularBags() end.

    # return a map.
    # key['piece','bol_ca']
    def __FlyerBenifit(self):
        pat = re.compile(r"\sFF/.")
        re_match = pat.search(self.__Pr)
        # 默认没有会员，也不是国航常旅客
        result = {"piece": 0, "bol_ca": False}
        if re_match:
            if self.__Pr[re_match.end()-1 : re_match.end() + 1] == "CA":
                result["bol_ca"] = True
        else:
            return result
        pat = re.compile(r"/\*G\s")
        re_match = pat.search(self.__Pr)
        # 如果是金卡，都有会员优惠。
        if re_match:
            result["piece"] = 1
        pat = re.compile(r"/\*S\s")
        re_match = pat.search(self.__Pr)
        # 如果是银卡的国航会员，才有优惠。
        if re_match and result["bol_ca"]:
            result["piece"] = 1

        self.debug_msg.append("flyer benif = " + str(result["piece"]))
        self.debug_msg.append("CA flyer    = " + str(result["bol_ca"]))
        return result

    # __FlyerBenifit() end.

    # return a map.
    # ['piece', 'weight']
    def __CalculateBagPieceAndWeight(self):
        expc = self.__ExpcStatement()
        index = 1
        asvc_tmp = {}
        asvc = 0  # Because the asvc result needs to accumulate.
        result = {"piece": 0, "weight": 0}
        arg = CArgs()
        while True:
            asvc_tmp = self.__AsvcBagStatement(index)
            if len(asvc_tmp) == 0:
                break
            else:
                index = asvc_tmp["index"]
                asvc = asvc + asvc_tmp["piece"]
        if expc:
            result["piece"] = expc["piece"] + asvc
            result["weight"] = expc["weight"] + asvc * arg.ClassBagWeight(
                self.__MainCls
            )
            self.debug_msg.append("total piece = " + str(result["piece"]))
            self.debug_msg.append("total weigh = " + str(result["weight"]))

            return result

        regular = self.__RegularBags()
        flyer = self.__FlyerBenifit()
        # 总件数=常旅客+网购+成人票+婴儿票
        result["piece"] = flyer["piece"] + asvc + regular["FBA"] + regular["IFBA"]
        if flyer["bol_ca"]:
            # 总重量 =（CA常旅客+网购+成人票） x 舱位重量
            result["weight"] = (
                flyer["piece"] + asvc + regular["FBA"]
            ) * arg.ClassBagWeight(self.__MainCls)
        else:
            # 总重量 = （非CA常旅客 x 金卡限制）+ （网购+成人票）x 舱位重量
            result["weight"] = flyer["piece"] * self.__FOREIGN_GOLD_FLYER_BAG_WEIGHT + (
                asvc + regular["FBA"]
            ) * arg.ClassBagWeight(self.__MainCls)
        if regular["IFBA"] != 0:
            # 总重量 附加 婴儿票重量。
            result["weight"] = result["weight"] + self.__INF_BAG_WEIGHT
        self.debug_msg.append("total piece = " + str(result["piece"]))
        self.debug_msg.append("total weigh = " + str(result["weight"]))
        return result

    # __CalulateBagPieceAndWeight() end.

    # Return a string.
    def __CaptureCkin(self):
        pat = re.compile(r"CKIN\sEXBG")
        re_match = pat.search(self.__Pr)
        ckin_msg = "CKIN not found."
        if re_match:
            ckin_msg = self.__Pr[re_match.start() : re_match.start() + 79]
        return ckin_msg

    # __CaptureCkin() end.

    def __MatchingBag(self):
        max_bag = self.__CalculateBagPieceAndWeight()
        if self.__ChkBagPcs > max_bag["piece"]:
            self.error_msg.append(
                "PR"
                + str(self.PrPdNumber)
                + "PD,\thas "
                + str(self.__ChkBagPcs - max_bag["piece"])
                + "extra bag(s)."
            )
            self.error_msg.append(self.__CaptureCkin())
            self.__BolError=True
        else:
            if self.__ChkBagTtlWeight > max_bag["weight"]:
                self.error_msg.append(
                    "PR"
                    + str(self.PrPdNumber)
                    + "PD,\tbaggage is overweight "
                    + str(self.__ChkBagTtlWeight - max_bag["weight"])
                    + "KGs."
                )
                self.error_msg.append(self.__CaptureCkin())
                self.__BolError=True
        return

    # Completion of baggage compareison.
    # ----------------------------------------------------

    def __GetName(self):
        try:
            namePat = re.compile(r"\d\.\s[A-Z/+\s]{3,17}")
            paxName = namePat.search(self.__Pr).group(0)
            paxName = paxName[3:]
            paxName = paxName.strip()
            self.debug_msg.append("pax name  = " + paxName)
        except:
            paxName = self.__ERROR_NUMBER
        return paxName

    # GetName() end.
    def __PsptName(self):
        try:
            namePat = re.compile(r"PAXLST   :[A-Z/]{3,}\s")
            paxName = namePat.search(self.__Pr).group(0)
            paxName = paxName.strip()
            paxName = paxName[10 : len(paxName) - 1]
            self.debug_msg.append("pspt name = " + paxName)
        except:
            paxName = self.__ERROR_NUMBER
        return paxName

    # PsptName() end.

    def __NameMatchMode1(self, ShortName, LongName):
        lstSuffix = ["MR", "MS", "MRS", "MSTR", "PHD", "CHD", "INF", "VIP"]

        # Remove suffixes from ShortName
        for suffix in lstSuffix:
            if ShortName.endswith(suffix):
                ShortName = ShortName[:-len(suffix)].rstrip()
                break

        # Remove suffixes from LongName
        for suffix in lstSuffix:
            if LongName.endswith(suffix):
                LongName = LongName[:-len(suffix)].rstrip()
                break

        lstShort = ShortName.split("/")
        lstLong = LongName.split("/")

        countMatch = 0
        for sh in lstShort:
            for lo in lstLong:
                if lo.find(sh) != -1:
                    countMatch += 1

        return countMatch > 1

    # NameMatchMode1() end.

    def __levenshtein_distance(self, s1, s2):
        # If the length of s1 is shorter than s2, swap them
        if len(s1) < len(s2):
            return self.__levenshtein_distance(s2, s1)

        # Create a distance matrix
        distances = range(len(s1) + 1)

        # Iterate over the characters of s2 and update the distances
        for index2, char2 in enumerate(s2):
            # Initialize a new list to store the updated distances
            new_distances = [index2 + 1]

            # Iterate over the characters of s1 and update the distances based on the characters' similarity
            for index1, char1 in enumerate(s1):
                # If the characters are equal, the distance remains the same
                if char1 == char2:
                    new_distances.append(distances[index1])
                else:
                    # Otherwise, the distance is the minimum of three possible operations: insert, delete, or substitute
                    new_distances.append(
                        1
                        + min(
                            (
                                distances[index1],
                                distances[index1 + 1],
                                new_distances[-1],
                            )
                        )
                    )

            # Update the distances list with the new_distances list
            distances = new_distances

        # The last element in the distances list represents the Levenshtein distance
        return distances[-1]

    def __NameMatchMode2(self, s1, s2):
        # Calculate the Levenshtein distance between the two strings
        distance = self.__levenshtein_distance(s1, s2)

        # Determine the maximum length of the input strings
        max_length = max(len(s1), len(s2))

        # Calculate the percentage difference based on the Levenshtein distance and the maximum length
        difference_percentage = 1 - distance / max_length

        if difference_percentage > 0.95:
            return True
        else:
            str_difference_percentage = str(
                "The Booking and Passport names match {0:.1%}"
            ).format(difference_percentage)
            self.error_msg.append(
                "PR"
                + str(self.PrPdNumber)
                + "PD,\t"
                + str_difference_percentage
            )
            self.__BolError=True
        return False

    # NameMatchMode2() end.

    def __NameMatch(self):
        recordName = self.__GetName()
        psptName = self.__PsptName()
        if recordName == self.__ERROR_NUMBER or psptName == self.__ERROR_NUMBER:
            self.error_msg.append(
                "PR"
                + str(self.PrPdNumber)
                + "PD,\tPAX name not found."
            )
            self.__BolError=True
            return
        longName, shortName = "", ""
        if len(recordName) >= len(psptName):
            shortName = psptName
            longName = recordName
        else:
            shortName = recordName
            longName = psptName
        bolMatch = self.__NameMatchMode1(shortName, longName)
        if bolMatch:
            self.debug_msg.append("Names are mactched.")
            return True
        else:
            bolMatch = self.__NameMatchMode2(shortName, longName)
        return False

    # __NameMatch() end.
    # Completion of Name Matching.
    # -------------------------------------------------------------------------------------------------

    def __GetPassportExp(self):
        psptPat = "PASSPORT :"
        indexS = self.__Pr.find(psptPat) + len(psptPat)
        indexE = self.__Pr.find(" ", indexS)
        lstPspt = self.__Pr[indexS:indexE].split("/")
        expDate = datetime.datetime.strptime(lstPspt[5], "%y%m%d")
        nextDate = datetime.datetime.now()
        deltaT = datetime.timedelta(days=1)
        nextDate = nextDate + deltaT
        if nextDate > expDate:
            errMsg = "The passport expired on %s." % expDate.strftime("%d%b%Y")
            self.error_msg.append(
                "PR"
                + str(self.PrPdNumber)
                + "PD,\t"
                + errMsg
            )
            self.__BolError=True
    # __GetPassportExpirationDate() end.
