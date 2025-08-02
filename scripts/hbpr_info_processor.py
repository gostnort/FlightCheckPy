#!/usr/bin/env python3
"""
HBPR Information Processor
Processes HBPR passenger records and validates/stores results.
"""

import re
import datetime
import sqlite3
import os
import glob
from .general_func import CArgs
from .hbpr_list_processor import HBPRProcessor


class CHbpr:
    """This class will process a single passenger information from HBPR page."""
    # 输出变量, 解析后的结构化数据字段 - 用于数据库存储
    error_msg = {"Baggage":[],"Passport":[],"Name":[],"Visa":[],"Other":[]}
    BoardingNumber = 0
    HbnbNumber = 0
    debug_msg = []
    PNR = ""
    NAME = ""
    SEAT = ""
    CLASS = ""
    DESTINATION = ""
    BAG_PIECE = 0
    BAG_WEIGHT = 0
    BAG_ALLOWANCE = 0
    FF = ""
    PSPT_NAME = ""
    PSPT_EXP_DATE = ""
    CKIN_MSG = []
    ASVC_MSG = []
    EXPC_PIECE = 0
    EXPC_WEIGHT = 0
    ASVC_PIECE = 0
    FBA_PIECE = 0
    IFBA_PIECE = 0
    FLYER_BENEFIT = 0
    INBOUND_FLIGHT = ""
    OUTBOUND_FLIGHT = ""
    PROPERTIES = []
    IS_CA_FLYER = False
    # 私有变量
    __ChkBagAverageWeight = 0
    __ERROR_NUMBER = 65535


    def __init__(self):
        super().__init__()


    def run(self, HbprContent: str):
        """处理HBPR记录的主要方法"""
        try:
            # 初始化所有类级变量
            self.debug_msg.clear()
            for key in self.error_msg:
                self.error_msg[key].clear()
            self.BoardingNumber = 0
            self.HbnbNumber = 0
            self.__ChkBagAverageWeight = 0
            self.__Hbpr = HbprContent
            # 初始化结构化数据字段
            self.PNR = ""
            self.NAME = ""
            self.SEAT = ""
            self.CLASS = ""
            self.DESTINATION = ""
            self.BAG_PIECE = 0
            self.BAG_WEIGHT = 0
            self.BAG_ALLOWANCE = 0
            self.FF = ""
            self.PSPT_NAME = ""
            self.PSPT_EXP_DATE = ""
            self.CKIN_MSG = []
            self.ASVC_MSG = []
            self.CKIN_EXBG = ""
            self.EXPC_PIECE = 0
            self.EXPC_WEIGHT = 0
            self.ASVC_PIECE = 0
            self.FBA_PIECE = 0
            self.IFBA_PIECE = 0
            self.FLYER_BENEFIT = 0
            self.IS_CA_FLYER = False
            self.PROPERTIES = []
            self.INBOUND_FLIGHT = ""
            self.OUTBOUND_FLIGHT = ""
            # 调用处理方法
            bolRun = True
            # 首先获取HBNB号码（用于错误消息）
            bolRun = self.__GetHbnbNumber()
            if bolRun:
                # 然后获取乘客信息（姓名、登机号、座位、舱位、目的地）
                bolRun = self.__GetPassengerInfo()
            if bolRun:
                self.__ExtractStructuredData()  # 新方法：提取结构化数据
                # 检查是否有BN号码，如果没有则跳过验证
                if self.BoardingNumber > 0:
                    self.__MatchingBag()
                    self.__GetPassportExp()
                    self.__GetVisaInfo()
                    self.__NameMatch()
                    self.__GetProperties()
                    self.__GetConnectingFlights()
                else:
                    self.debug_msg.append("No BN number found, skipping validation")
        except Exception as e:
            self.error_msg["Other"].append(
                f"A Fatal Error occurred at HBPR{self.HbnbNumber}; "
                f"Boarding Number should be {self.BoardingNumber}. Error: {str(e)}"
            )


    def __del__(self):
        self.debug_msg.append(
            f"Boarding number {self.BoardingNumber}. \nCHbpr deconstruction."
        )


    def __GetHbnbNumber(self):
        """单独获取HBNB号码"""
        hbnbPat = re.compile(r">HBPR:\s*[^,]+,(\d+)")
        hbnbMatch = hbnbPat.search(self.__Hbpr)
        if hbnbMatch:
            try:
                self.HbnbNumber = int(hbnbMatch.group(1))
                self.debug_msg.append("HBNB number = " + str(self.HbnbNumber))
                return True
            except:
                self.HbnbNumber = self.__ERROR_NUMBER
                return False
        return False


    def __GetPassengerInfo(self):
        """一次性获取姓名、登机号、座位、舱位目的地"""
        # 搜索乘客信息行（包含姓名的行）
        namePat = re.compile(r"(\d\.\s)([A-Z/+\s]{3,17})")
        nameMatch = namePat.search(self.__Hbpr)
        if not nameMatch:
            self.error_msg["Other"].append(f"HBPR{self.HbnbNumber},\tPassenger name not found.")
            return False
        # 获取姓名
        self.NAME = nameMatch.group(2).strip()
        self.debug_msg.append("pax name  = " + self.NAME)
        # 从姓名行找到行的结束位置，获取整行内容进行后续解析
        name_end_index = self.__Hbpr.find('\n', nameMatch.end())
        if name_end_index == -1:
            name_end_index = len(self.__Hbpr)
        name_row = self.__Hbpr[nameMatch.start():name_end_index]
        # 在姓名行中搜索登机号（可选）
        bnPat = re.compile(r"BN(\d{3})")
        bnMatch = bnPat.search(name_row)
        search_start = 1
        if bnMatch:
            try:
                self.BoardingNumber = int(bnMatch.group(1))
                self.debug_msg.append("boarding # = " + str(self.BoardingNumber))
                search_start = bnMatch.end()  # 如果有BN，从BN后开始搜索
            except:
                self.BoardingNumber = self.__ERROR_NUMBER
        # 搜索座位（在姓名/BN之后，舱位之前）
        # 座位格式：可能带*的数字+字母，如 "14H", "*13D"
        seatPat = re.compile(r"\s+\*?(\d{1,2}[A-Z])\s+")
        seatMatch = seatPat.search(name_row, search_start)
        if seatMatch:
            self.SEAT = seatMatch.group(1)
            self.debug_msg.append("seat = " + self.SEAT)
            search_start = seatMatch.end()
        # 搜索舱位（在座位之后）
        clsPat = re.compile(r"([A-Z])\s+")
        if search_start < 38:
            search_start = 38
        clsMatch = clsPat.search(name_row, search_start)
        if clsMatch:
            sub_class = clsMatch.group(1)
            # 转换为主舱位
            fltArgs = CArgs()
            self.CLASS = fltArgs.SubCls2MainCls(sub_class)
            self.debug_msg.append("class = " + self.CLASS)
            search_start = clsMatch.end()
            # 搜索目的地（在舱位之后）
            destPat = re.compile(r"([A-Z]{3})")
            destMatch = destPat.search(name_row, search_start)
            if destMatch:
                self.DESTINATION = destMatch.group(1)
                self.debug_msg.append("destination = " + self.DESTINATION)
        else:
            self.error_msg["Other"].append(f"HBPR{self.HbnbNumber},\tNone validity classes are found.")
            return False
        return True


    def __ExtractStructuredData(self):
        """提取结构化数据字段"""
        # 提取PNR
        pnr_match = re.search(r'PNR\s+RL\s+([A-Z0-9]+)', self.__Hbpr)
        if pnr_match:
            self.PNR = pnr_match.group(1)
        # 提取护照姓名
        self.PSPT_NAME = self.__PsptName()
        if self.PSPT_NAME == self.__ERROR_NUMBER:
            self.PSPT_NAME = ""
        # 提取常规行李额度
        regular_bags = self.__RegularBags()
        if regular_bags:
            self.FBA_PIECE = regular_bags.get("FBA")
            self.IFBA_PIECE = regular_bags.get("IFBA")
        # 提取托运行李
        self.__GetChkBag()
        # 提取常旅客权益
        self.__FlyerBenifit()
        # 提取CKIN信息
        self.CKIN_EXBG = self.__CaptureCkin()
        return


    def __GetChkBag(self):
        """获取托运行李信息"""
        pat = re.compile(r"BAG(\d{1,2})/(\d{1,3})/\d+\s")
        re_match = pat.search(self.__Hbpr)
        if re_match:
            self.BAG_PIECE = int(re_match.group(1))
            self.BAG_WEIGHT = int(re_match.group(2))
        else:
            self.BAG_PIECE = 0
            self.BAG_WEIGHT = 0
        # HBPR格式中行李信息可能不同，这里简化处理
        # 如果没有明确的行李标签，设为默认值
        if self.BAG_PIECE == 0:
            self.__ChkBagAverageWeight = 0
        else:
            self.__ChkBagAverageWeight = self.BAG_WEIGHT / self.BAG_PIECE
        self.debug_msg.append("bag piece  = " + str(self.BAG_PIECE))
        self.debug_msg.append("bag total w= " + str(self.BAG_WEIGHT))
        self.debug_msg.append("bag averag = " + str(self.__ChkBagAverageWeight))


    def __ExpcStatement(self):
        """处理EXPC语句"""
        pat = re.compile(r"EXPC-\s")
        re_match = pat.search(self.__Hbpr)
        result = {}
        if re_match is None:
            return result
        # 插入EXPC数量
        try:
            result["piece"] = int(self.__Hbpr[re_match.end()])
        except ValueError:
            self.debug_msg.append("expc piece type error.")
        w_total = 0
        end_index = 1
        pat = re.compile(r"/\d{1,2}KG-")
        while True:
            re_match = pat.search(self.__Hbpr, end_index)
            if re_match is None:
                break
            w = self.__Hbpr[re_match.start() + 1 : re_match.end() - 3]
            try:
                w_int = int(w)
            except:
                self.debug_msg.append("expc ttl w type error.")
            w_total = w_total + w_int
            end_index = re_match.end()
        # 插入EXPC总重量
        result["weight"] = w_total
        self.EXPC_PIECE = result["piece"]
        self.EXPC_WEIGHT = w_total
        self.debug_msg.append("expc piece = " + str(result.get("piece", 0)))
        self.debug_msg.append("expc ttl w = " + str(result["weight"]))
        return result


    def __AsvcBagStatement(self):
        """处理ASVC行李语句"""
        # 查找所有ASVC-消息
        asvc_pat = re.compile(r"ASVC-[^\n]*")
        asvc_matches = asvc_pat.findall(self.__Hbpr)
        result_piece = 0
        if asvc_matches:
            for match in asvc_matches:
                self.ASVC_MSG.append(match.strip())
        else:
            return result_piece
        # 遍历所有ASVC行
        for asvc_line in asvc_matches:
            # 查找该行中所有的PC数量
            pc_pat = re.compile(r"/PDBG/(\d+)PC")
            pc_matches = pc_pat.findall(asvc_line)
            # 累加所有PC数量
            for pc_count in pc_matches:
                try:
                    pieces = int(pc_count)
                    result_piece += pieces
                    self.debug_msg.append(f"asvc bag found {pieces} PC in line: {asvc_line[:50]}...")
                except ValueError:
                    self.debug_msg.append(f"asvc bag PC type error in: {asvc_line[:50]}...")
        if result_piece > 0:
            self.debug_msg.append(f"asvc total pieces = {result_piece}")
        self.ASVC_PIECE = result_piece
        return result_piece


    def __RegularBags(self):
        """获取常规行李额度"""
        # 一般订座都有FBA项目
        pat = re.compile(r"\sFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        result = {"FBA": 0, "IFBA": 0}
        if re_match:
            try:
                result["FBA"] = int(self.__Hbpr[re_match.start() + 5])
            except:
                self.error_msg["Other"].append(
                    f"HBPR{self.HbnbNumber},\tFBA got an error."
                )
        # 婴儿票有IFBA项目
        pat = re.compile(r"\sIFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        if re_match:
            result["IFBA"] = 1
        self.FBA_PIECE = result["FBA"]
        self.IFBA_PIECE = result["IFBA"]
        # 员工票客只能使用默认的行李额度
        pat = re.compile(r"\sPAD-SA\s")
        re_match = pat.search(self.__Hbpr)
        if re_match:
            result["FBA"] = 2
        self.debug_msg.append("adult bag  = " + str(result["FBA"]))
        self.debug_msg.append("Infant bag = " + str(result["IFBA"]))
        return result


    def __FlyerBenifit(self):
        """获取常旅客权益"""
        # 查找FF模式并提取FF号码 - 修复正则表达式以正确提取FF信息
        ff_pat = re.compile(r"FF/([A-Z]{2}\s[A-Z0-9]+/[A-Z](?:/\*[GS])?)")
        ff_match = ff_pat.search(self.__Hbpr)
        # 默认没有会员，也不是国航常旅客
        result = {"piece": 0, "bol_ca": False}
        if ff_match:
            # 提取FF号码：如 "CA 002151005024/G/*G" 或 "CA 002151005024/B"
            self.FF = ff_match.group(1)
            self.debug_msg.append("FF number = " + self.FF)
            match_content = self.__Hbpr[ff_match.start():ff_match.end()]
            self.debug_msg.append("FF match content = " + match_content)
            # 检查是否为国航会员
            if self.FF.startswith("CA"):
                result["bol_ca"] = True
            # 查找金卡标识 /*G
            if "/*G" in match_content:
                result["piece"] = 1
                self.debug_msg.append("Found Gold Card /*G")
            # 查找银卡标识 /*S (只对国航会员有效)
            elif "/*S" in match_content and result["bol_ca"]:
                result["piece"] = 1
                self.debug_msg.append("Found Silver Card /*S")
        else:
            self.FF = ""
            self.debug_msg.append("No FF match found")
        self.debug_msg.append("flyer benif = " + str(result["piece"]))
        self.debug_msg.append("CA flyer    = " + str(result["bol_ca"]))
        self.FLYER_BENEFIT = result["piece"]
        self.IS_CA_FLYER = result["bol_ca"]
        return result


    def __CalculateBagPieceAndWeight(self):
        """计算行李件数和重量"""
        self.__ExpcStatement() # 函数结果已经共享给EXPC_PIECE和EXPC_WEIGHT
        asvc_piece = self.__AsvcBagStatement()
        result = {"piece": 0, "weight": 0}
        arg = CArgs()
        # 总件数=常旅客+网购+成人票+婴儿票
        result["piece"] = self.FLYER_BENEFIT + asvc_piece + self.FBA_PIECE + self.IFBA_PIECE
        if self.IS_CA_FLYER:
            # 总重量 =（CA常旅客+网购+成人票） x 舱位重量
            result["weight"] = (
                self.FLYER_BENEFIT + self.FBA_PIECE + asvc_piece
            ) * arg.ClassBagWeight(self.CLASS)
        else:
            # 总重量 = （非CA常旅客 x 金卡限制）+ （网购+成人票）x 舱位重量
            result["weight"] = self.FLYER_BENEFIT * arg.ForeignGoldFlyerBagWeight() + (
                self.FBA_PIECE + asvc_piece
            ) * arg.ClassBagWeight(self.CLASS)
        if self.IFBA_PIECE != 0:
            # 总重量 附加 婴儿票重量
            result["weight"] = result["weight"] + arg.InfBagWeight()
        if result["weight"] < self.EXPC_WEIGHT:
            result["weight"] = self.EXPC_WEIGHT
        if result["piece"] < self.EXPC_PIECE:
            result["piece"] = self.EXPC_PIECE
        self.debug_msg.append("total piece = " + str(result["piece"]))
        self.debug_msg.append("total weigh = " + str(result["weight"]))
        return result


    def __CaptureCkin(self):
        """
        捕获CKIN信息，并设置CKIN_MSG字段
        搜索所有以'CKIN '开头的行
        如果CKIN信息不存在，则设置CKIN_MSG字段为"CKIN not found."
        只返回CKIN EXBG信息,如果有的话。
        """
        # 清空之前的CKIN_MSG列表
        self.CKIN_MSG.clear()
        # 使用findall来找到所有匹配的CKIN行
        pat = re.compile(r"CKIN\s+[^\n]*")
        re_matches = pat.findall(self.__Hbpr)
        if re_matches:
            # 将所有找到的CKIN行添加到列表中
            for match in re_matches:
                self.CKIN_MSG.append(match.strip())
        else:
            #self.CKIN_MSG.append("CKIN not found.")
            return "CKIN not found."
        # 查找EXBG信息
        for msg in self.CKIN_MSG:
            if "EXBG" in msg:
                self.CKIN_EXBG = msg
                return msg
        return "CKIN EXBG not found."


    def __MatchingBag(self):
        """匹配行李"""
        max_bag = self.__CalculateBagPieceAndWeight()
        args = CArgs()
        bol_ckin_exbg = False
        if max_bag:
            self.BAG_ALLOWANCE = max_bag.get("piece")
        if self.BAG_PIECE > max_bag["piece"]:
            self.error_msg["Baggage"].append(
                f"HBPR{self.HbnbNumber},\thas "
                f"{self.BAG_PIECE - max_bag['piece']} extra bag(s)."
            )
            bol_ckin_exbg = True
        elif self.BAG_WEIGHT > max_bag["weight"]:
            if self.BAG_WEIGHT > args.ClassBagWeight(self.CLASS) * self.BAG_PIECE:
                self.error_msg["Baggage"].append(
                    f"HBPR{self.HbnbNumber},the baggage is overweight "
                    f"{self.BAG_WEIGHT - max_bag['weight']} KGs."
                )
                bol_ckin_exbg = True
        elif self.__ChkBagAverageWeight > (max_bag["weight"] / max_bag["piece"]):
            if self.__ChkBagAverageWeight > args.ClassBagWeight(self.CLASS):
                self.error_msg["Baggage"].append(
                    f"HBPR{self.HbnbNumber},the baggage average weight is overweight "
                    f"{self.__ChkBagAverageWeight - (max_bag['weight'] / max_bag['piece'])} KGs."
                )
                bol_ckin_exbg = True
        if bol_ckin_exbg:
            self.error_msg["Baggage"].append(self.CKIN_EXBG)
        return


    def __PsptName(self):
        """获取护照姓名"""
        try:
            namePat = re.compile(r"PAXLST\s*:([A-Z/]+)")
            match = namePat.search(self.__Hbpr)
            if match:
                paxName = match.group(1).strip().rstrip('/')
                self.debug_msg.append("pspt name = " + paxName)
            else:
                paxName = self.__ERROR_NUMBER
        except:
            paxName = self.__ERROR_NUMBER
        return paxName


    def __NameMatchMode1(self, ShortName, LongName):
        """姓名匹配模式1"""
        lstSuffix = ["MR", "MS", "MRS", "MSTR", "PHD", "CHD", "INF", "VIP"]
        # 移除ShortName的后缀
        for suffix in lstSuffix:
            if ShortName.endswith(suffix):
                ShortName = ShortName[:-len(suffix)].rstrip()
                break
        # 移除LongName的后缀
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


    def __levenshtein_distance(self, s1, s2):
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self.__levenshtein_distance(s2, s1)
        distances = range(len(s1) + 1)
        for index2, char2 in enumerate(s2):
            new_distances = [index2 + 1]
            for index1, char1 in enumerate(s1):
                if char1 == char2:
                    new_distances.append(distances[index1])
                else:
                    new_distances.append(
                        1 + min((distances[index1], distances[index1 + 1], new_distances[-1]))
                    )
            distances = new_distances
        return distances[-1]


    def __NameMatchMode2(self, s1, s2):
        """姓名匹配模式2"""
        distance = self.__levenshtein_distance(s1, s2)
        max_length = max(len(s1), len(s2))
        difference_percentage = 1 - distance / max_length
        if difference_percentage > 0.95:
            return True
        else:
            str_difference_percentage = f"The Booking and Passport names match {difference_percentage:.1%}"
            self.error_msg["Name"].append(
                f"HBPR{self.HbnbNumber},\t{str_difference_percentage}"
            )
        return False


    def __NameMatch(self):
        """执行姓名匹配"""
        recordName = self.NAME
        psptName = self.PSPT_NAME
        if recordName == self.__ERROR_NUMBER or psptName == self.__ERROR_NUMBER:
            self.error_msg["Name"].append(
                f"HBPR{self.HbnbNumber},\tPAX name not found."
            )
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
            self.debug_msg.append("Names are matched.")
            return True
        else:
            bolMatch = self.__NameMatchMode2(shortName, longName)
        return False


    def __GetPassportExp(self):
        """获取护照到期日期"""
        try:
            psptPat = "PASSPORT :"
            indexS = self.__Hbpr.find(psptPat) + len(psptPat)
            indexE = self.__Hbpr.find(" ", indexS)
            lstPspt = self.__Hbpr[indexS:indexE].split("/")
            if len(lstPspt) >= 6:
                expDate = datetime.datetime.strptime(lstPspt[5], "%y%m%d")
                self.PSPT_EXP_DATE = expDate.strftime('%Y-%m-%d')  # 保存护照到期日期
                nextDate = datetime.datetime.now()
                deltaT = datetime.timedelta(days=1)
                nextDate = nextDate + deltaT
                if nextDate > expDate:
                    errMsg = f"The passport expired on {expDate.strftime('%d%b%Y')}."
                    self.error_msg["Passport"].append(
                        f"HBPR{self.HbnbNumber},\t{errMsg}"
                    )
        except Exception as e:
            self.debug_msg.append(f"Passport expiration check failed: {str(e)}")


    def __GetVisaInfo(self):
        """获取签证信息"""
        # 首先从护照信息中提取国籍
        nationality = ""
        try:
            psptPat = "PASSPORT :"
            indexS = self.__Hbpr.find(psptPat) + len(psptPat)
            indexE = self.__Hbpr.find(" ", indexS)
            lstPspt = self.__Hbpr[indexS:indexE].split("/")
            if len(lstPspt) >= 4:
                nationality = lstPspt[3]  # 国籍在第4个位置
                self.debug_msg.append(f"passport nationality = {nationality}")
        except Exception as e:
            self.debug_msg.append(f"Failed to extract nationality: {str(e)}")
            return
        # 如果国籍不是中国，检查签证信息
        if nationality and nationality != "CHN" and nationality != "CN":
            # 检查VISA INFO模式
            visa_info_pat = re.compile(r"VISA INFO:")
            visa_info_match = visa_info_pat.search(self.__Hbpr)
            # 检查CKIN VISA模式
            ckin_visa_pat = re.compile(r"CKIN VISA")
            ckin_visa_match = ckin_visa_pat.search(self.__Hbpr)
            if visa_info_match or ckin_visa_match:
                # 找到签证信息，记录调试信息
                if visa_info_match:
                    self.debug_msg.append("VISA INFO found")
                if ckin_visa_match:
                    self.debug_msg.append("CKIN VISA found")
            else:
                # 未找到签证信息，添加错误
                self.error_msg["Visa"].append(
                    f"HBPR{self.HbnbNumber},\tNo visa information found for {nationality} passport holder\n"
                    f"PAX: {self.NAME}, BN: {self.BoardingNumber}"
                )
        return


    def get_structured_data(self):
        """返回结构化数据字典，用于数据库存储"""
        return {
            'hbnb_number': self.HbnbNumber,
            'boarding_number': self.BoardingNumber,
            'PNR': self.PNR,
            'NAME': self.NAME,
            'SEAT': self.SEAT,
            'CLASS': self.CLASS,
            'DESTINATION': self.DESTINATION,
            'BAG_PIECE': self.BAG_PIECE,
            'BAG_WEIGHT': self.BAG_WEIGHT,
            'BAG_ALLOWANCE': self.BAG_ALLOWANCE,
            'FF': self.FF,
            'PSPT_NAME': self.PSPT_NAME,
            'PSPT_EXP_DATE': self.PSPT_EXP_DATE,
            'CKIN_MSG': '; '.join(self.CKIN_MSG) if self.CKIN_MSG else '',
            'ASVC_MSG': '; '.join(self.ASVC_MSG) if self.ASVC_MSG else '',
            'EXPC_PIECE': self.EXPC_PIECE,
            'EXPC_WEIGHT': self.EXPC_WEIGHT,
            'ASVC_PIECE': self.ASVC_PIECE,
            'FBA_PIECE': self.FBA_PIECE,
            'IFBA_PIECE': self.IFBA_PIECE,
            'FLYER_BENEFIT': self.FLYER_BENEFIT,
            'IS_CA_FLYER': self.IS_CA_FLYER,
            'INBOUND_FLIGHT': self.INBOUND_FLIGHT,
            'OUTBOUND_FLIGHT': self.OUTBOUND_FLIGHT,
            'PROPERTIES': ','.join(self.PROPERTIES) if self.PROPERTIES else '',
            'has_error': any(self.error_msg.values()),
            'error_baggage': '\n'.join(self.error_msg["Baggage"]) if self.error_msg["Baggage"] else '',
            'error_passport': '\n'.join(self.error_msg["Passport"]) if self.error_msg["Passport"] else '',
            'error_name': '\n'.join(self.error_msg["Name"]) if self.error_msg["Name"] else '',
            'error_visa': '\n'.join(self.error_msg["Visa"]) if self.error_msg["Visa"] else '',
            'error_other': '\n'.join(self.error_msg["Other"]) if self.error_msg["Other"] else '',
            'error_count': sum(1 for value in self.error_msg.values() if value)
        }


    def __GetConnectingFlights(self):
        """获取连接航班"""
        result = {}
        # 获取进港航班
        inbound_pattern = r"\s(I/[A-Z]{2}\d+/\d{2}[A-Z]{3})\s"
        inbound_match = re.search(inbound_pattern, self.__Hbpr)
        if inbound_match:
            self.INBOUND_FLIGHT = inbound_match.group(1).replace("I/", "")
            result["inbound_station"] = self.__Hbpr[inbound_match.start()+37:inbound_match.start()+40]
        else:
            self.INBOUND_FLIGHT = ""
            result["inbound_station"] = ""
        # 获取出港航班
        outbound_pattern = r"\s(O/[A-Z]{2}\d+/\d{2}[A-Z]{3})\s"
        outbound_match = re.search(outbound_pattern, self.__Hbpr)
        if outbound_match:
            self.OUTBOUND_FLIGHT = outbound_match.group(1).replace("O/", "")
            result["outbound_station"] = self.__Hbpr[outbound_match.start()+37:outbound_match.start()+40]
            self.DESTINATION = result['outbound_station']
        else:
            self.OUTBOUND_FLIGHT = ""
            result["outbound_station"] = ""
        self.debug_msg.append(f"INBOUND_FLIGHT = {self.INBOUND_FLIGHT}, OUTBOUND_FLIGHT = {self.OUTBOUND_FLIGHT}")
        self.debug_msg.append(f"INBOUND_STATION = {result['inbound_station']}, OUTBOUND_STATION = {result['outbound_station']}")
        return result
    

    def __GetProperties(self):
        """获取属性"""
        # 读取姓名行以及后面包含40个空格开头的行
        properties_lines = []
        for line in self.__Hbpr.split("\n"):
            if line.startswith(" " * 40):
                new_line = line[40:]
                properties_lines.append(new_line)
                continue
            if line.startswith("  1."):
                new_line = line[40:]
                properties_lines.append(new_line)
                continue
        properties = []
        for line in properties_lines:
            current_property = line.split(" ")
            properties.extend(current_property)
        
        #删除没用的属性
        properties_to_remove = []
        for property in properties:
            if any([
                len(property) == 1,  # 删除舱位
                property.startswith("R"),  # 删除座位
                property.startswith("ESTA"),  # 删除ESTA
                property in ['PEK', 'LAX'],  # 删除目的地
                property.startswith("TKNE"),  # 删除TKNE
                property.startswith("FF/"),  # 删除FF属性
                property.startswith("FBA"),  # 删除FBA的变化
                property.startswith("IFBA"),  # 删除IFBA的变化
                property == "ASR",  # 删除ASR
                property == "RES",  # 删除RES
                property == "OSR",  # 删除OSR
                property == "ABP",  # 删除ABP
                property.startswith("SNR"),  # 删除SNR的座位
                property in ["M1/0", "F1/0"],  # 删除性别
                property.startswith("BAG"),  # 删除BAG
                property.startswith("FOID/"),  # 删除FOID
                property.startswith("OSR"),  # 删除OSR
                property.startswith("TMC")  # 删除TMC
            ]):
                properties_to_remove.append(property)
        # 删除不需要的属性
        for property in properties_to_remove:
            if property in properties:
                if property.startswith("FF/"):#FF号码后面一个属性是FF的会员号
                    index = properties.index(property)
                    properties.remove(property) 
                    properties.remove(properties[index]) #紧跟其后的FF会员号会马上替代原来的index
                    continue
                else:
                    properties.remove(property)
        self.PROPERTIES = properties
        return 


    def is_valid(self):
        """检查记录是否通过验证（无错误）"""
        return not any(self.error_msg.values())




class HbprDatabase:
    """数据库操作类，管理HBPR相关的所有数据库操作"""
    
    def __init__(self, db_file: str = None):
        """初始化数据库连接"""
        # Initialize cache before setting db_file
        self._chbpr_fields_initialized = False  # Cache to avoid repeated field additions
        self.db_file = db_file
        if db_file and not os.path.exists(db_file):
            raise FileNotFoundError(f"Database file {db_file} not found!")
    
    
    def find_database(self):
        """查找包含HBPR数据的数据库文件，优先查找databases文件夹"""
        # 首先查找databases文件夹中的数据库文件
        databases_folder = "databases"
        if os.path.exists(databases_folder):
            db_files = glob.glob(os.path.join(databases_folder, "*.db"))
        else:
            db_files = []
        
        # 如果databases文件夹中没有找到，则查找根目录
        if not db_files:
            db_files = glob.glob("*.db")
        
        if not db_files:
            raise FileNotFoundError("No database files found! Please build database first.")
        
        for db_file in db_files:
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_full_records'")
                if cursor.fetchone():
                    conn.close()
                    # Reset cache if database file changes
                    if self.db_file != db_file:
                        self._chbpr_fields_initialized = False
                    self.db_file = db_file
                    # 确保数据库有最新的字段结构
                    self._add_chbpr_fields()
                    return db_file
                conn.close()
            except sqlite3.Error:
                continue
        
        raise FileNotFoundError("No database with hbpr_full_records table found!")
    
    
    def build_from_hbpr_list(self, input_file: str = "sample_hbpr_list.txt"):
        """使用hbpr_list_processor从文件构建数据库"""
        print(f"=== Building database from {input_file} ===")
        
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file {input_file} not found!")
        
        # 创建处理器并处理文件
        processor = HBPRProcessor(input_file)
        processor.process()
        
        # 更新数据库文件路径
        self.find_database()
        
        # 添加CHbpr字段到hbpr_full_records表
        self._add_chbpr_fields()
        
        # 初始化missing_numbers表
        try:
            self.update_missing_numbers_table()
            print("Missing numbers table initialized")
        except Exception as e:
            print(f"Warning: Could not initialize missing numbers table: {e}")
        
        print(f"Database built successfully: {self.db_file}")
        return processor
    
    
    def _add_chbpr_fields(self):
        """向hbpr_full_records表添加CHbpr解析的字段"""
        if not self.db_file:
            self.find_database()
        
        # Skip if already initialized for this database instance
        if self._chbpr_fields_initialized:
            return
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # 定义需要添加的字段
            new_fields = [
                ('is_validated', 'BOOLEAN DEFAULT 0'),
                ('is_valid', 'BOOLEAN'),
                ('boarding_number', 'INTEGER'),
                ('pnr', 'TEXT'),
                ('name', 'TEXT'),
                ('seat', 'TEXT'),
                ('class', 'TEXT'),
                ('destination', 'TEXT'),
                ('bag_piece', 'INTEGER'),
                ('bag_weight', 'INTEGER'),
                ('bag_allowance', 'INTEGER'),
                ('ff', 'TEXT'),
                ('pspt_name', 'TEXT'),
                ('pspt_exp_date', 'TEXT'),
                ('ckin_msg', 'TEXT'),
                ('asvc_msg', 'TEXT'),
                ('expc_piece', 'INTEGER'),
                ('expc_weight', 'INTEGER'),
                ('asvc_piece', 'INTEGER'),
                ('fba_piece', 'INTEGER'),
                ('ifba_piece', 'INTEGER'),
                ('flyer_benefit', 'INTEGER'),
                ('is_ca_flyer', 'BOOLEAN'),
                ('inbound_flight', 'TEXT'),
                ('outbound_flight', 'TEXT'),
                ('properties', 'TEXT'),
                ('error_count', 'INTEGER'),
                ('error_baggage', 'TEXT'),
                ('error_passport', 'TEXT'),
                ('error_name', 'TEXT'),
                ('error_visa', 'TEXT'),
                ('error_other', 'TEXT'),
                ('validated_at', 'TIMESTAMP'),
                ('bol_duplicate', 'BOOLEAN DEFAULT 0')
            ]
            
            # 添加不存在的字段
            fields_added = 0
            for field_name, field_type in new_fields:
                if field_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE hbpr_full_records ADD COLUMN {field_name} {field_type}")
                        print(f"Added field: {field_name}")
                        fields_added += 1
                    except sqlite3.Error as e:
                        print(f"Warning: Could not add field {field_name}: {e}")
            
            conn.commit()
            conn.close()
            
            # Only print summary message if fields were actually added
            if fields_added > 0:
                print(f"CHbpr fields added to hbpr_full_records table ({fields_added} new fields)")
            
            # Mark as initialized for this instance
            self._chbpr_fields_initialized = True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_hbpr_record(self, hbnb_number: int):
        """从数据库获取HBPR记录内容"""
        if not self.db_file:
            self.find_database()
        else:
            # 确保数据库有最新的字段结构
            self._add_chbpr_fields()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT record_content FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                raise ValueError(f"No HBPR record found for HBNB {hbnb_number}")
                
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def update_with_chbpr_results(self, chbpr_instance: CHbpr):
        """使用CHbpr实例的结果更新hbpr_full_records表"""
        if not self.db_file:
            self.find_database()
        else:
            # 确保数据库有最新的字段结构
            self._add_chbpr_fields()
        
        # 获取结构化数据
        data = chbpr_instance.get_structured_data()
        hbnb_number = data['hbnb_number']
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查记录是否存在
            cursor.execute("SELECT 1 FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            if not cursor.fetchone():
                raise ValueError(f"HBNB {hbnb_number} not found in hbpr_full_records")
            
            # 更新记录
            cursor.execute('''
                UPDATE hbpr_full_records SET
                    is_validated = 1,
                    is_valid = ?,
                    boarding_number = ?,
                    pnr = ?,
                    name = ?,
                    seat = ?,
                    class = ?,
                    destination = ?,
                    bag_piece = ?,
                    bag_weight = ?,
                    bag_allowance = ?,
                    ff = ?,
                    pspt_name = ?,
                    pspt_exp_date = ?,
                    ckin_msg = ?,
                    asvc_msg = ?,
                    expc_piece = ?,
                    expc_weight = ?,
                    asvc_piece = ?,
                    fba_piece = ?,
                    ifba_piece = ?,
                    flyer_benefit = ?,
                    is_ca_flyer = ?,
                    inbound_flight = ?,
                    outbound_flight = ?,
                    properties = ?,
                    error_count = ?,
                    error_baggage = ?,
                    error_passport = ?,
                    error_name = ?,
                    error_visa = ?,
                    error_other = ?,
                    validated_at = CURRENT_TIMESTAMP
                WHERE hbnb_number = ?
            ''', (
                chbpr_instance.is_valid(),
                data['boarding_number'],
                data['PNR'],
                data['NAME'],
                data['SEAT'],
                data['CLASS'],
                data['DESTINATION'],
                data['BAG_PIECE'],
                data['BAG_WEIGHT'],
                data['BAG_ALLOWANCE'],
                data['FF'],
                data['PSPT_NAME'],
                data['PSPT_EXP_DATE'],
                data['CKIN_MSG'],
                data['ASVC_MSG'],
                data['EXPC_PIECE'],
                data['EXPC_WEIGHT'],
                data['ASVC_PIECE'],
                data['FBA_PIECE'],
                data['IFBA_PIECE'],
                data['FLYER_BENEFIT'],
                data['IS_CA_FLYER'],
                data['INBOUND_FLIGHT'],
                data['OUTBOUND_FLIGHT'],
                data['PROPERTIES'],
                data['error_count'],
                data['error_baggage'],
                data['error_passport'],
                data['error_name'],
                data['error_visa'],
                data['error_other'],
                hbnb_number
            ))
            
            conn.commit()
            conn.close()
            
            print(f"Updated HBNB {hbnb_number} in hbpr_full_records table")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_validation_stats(self):
        """获取验证统计信息"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            total_records = cursor.fetchone()[0]
            
            # 已验证记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1")
            validated_records = cursor.fetchone()[0]
            
            # 有效记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_valid = 1")
            valid_records = cursor.fetchone()[0]
            
            # 无效记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1 AND is_valid = 0")
            invalid_records = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_records': total_records,
                'validated_records': validated_records,
                'valid_records': valid_records,
                'invalid_records': invalid_records
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_missing_hbnb_numbers(self):
        """获取缺失的HBNB号码列表"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查是否存在missing_numbers表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='missing_numbers'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            # 获取缺失的HBNB号码
            cursor.execute("SELECT hbnb_number FROM missing_numbers ORDER BY hbnb_number")
            missing_numbers = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return missing_numbers
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")



    def update_missing_numbers_table(self):
        """重新计算并更新missing_numbers表"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查是否存在missing_numbers表，如果不存在则创建
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='missing_numbers'")
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE missing_numbers (
                        hbnb_number INTEGER PRIMARY KEY
                    )
                ''')
                print("Created missing_numbers table")
            
            # 获取所有现有的HBNB号码（包括完整记录和简单记录）
            cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
            full_records = [row[0] for row in cursor.fetchall()]
            
            # 检查是否存在hbpr_simple_records表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("SELECT hbnb_number FROM hbpr_simple_records ORDER BY hbnb_number")
                simple_records = [row[0] for row in cursor.fetchall()]
            else:
                simple_records = []
            
            # 合并所有HBNB号码
            all_hbnb_numbers = set(full_records + simple_records)
            
            if not all_hbnb_numbers:
                conn.close()
                return False
            
            # 计算期望的范围
            min_num = min(all_hbnb_numbers)
            max_num = max(all_hbnb_numbers)
            expected_numbers = set(range(min_num, max_num + 1))
            
            # 计算缺失的号码
            missing_numbers = expected_numbers - all_hbnb_numbers
            
            # 清空现有的missing_numbers表
            cursor.execute("DELETE FROM missing_numbers")
            
            # 插入新的缺失号码
            for num in sorted(missing_numbers):
                cursor.execute("INSERT INTO missing_numbers (hbnb_number) VALUES (?)", (num,))
            
            conn.commit()
            conn.close()
            
            print(f"Updated missing_numbers table: {len(missing_numbers)} missing numbers")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_hbnb_range_info(self):
        """获取HBNB号码范围信息"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 获取所有HBNB号码
            cursor.execute("SELECT hbnb_number FROM hbpr_full_records ORDER BY hbnb_number")
            hbnb_numbers = [row[0] for row in cursor.fetchall()]
            
            if not hbnb_numbers:
                conn.close()
                return {'min': 0, 'max': 0, 'total_expected': 0, 'total_found': 0}
            
            min_num = min(hbnb_numbers)
            max_num = max(hbnb_numbers)
            total_found = len(hbnb_numbers)
            
            # 计算期望的总数（连续范围）
            total_expected = max_num - min_num + 1
            
            conn.close()
            
            return {
                'min': min_num,
                'max': max_num,
                'total_expected': total_expected,
                'total_found': total_found
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def erase_splited_records(self):
        """删除hbpr_full_records表中除hbnb_number和record_content外的所有记录"""
        if not self.db_file:
            self.find_database()
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 获取当前记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            total_records = cursor.fetchone()[0]
            
            # 获取表的所有列名
            cursor.execute("PRAGMA table_info(hbpr_full_records)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"发现表字段: {column_names}")
            
            # 找出需要清除的字段（除了hbnb_number和record_content）
            fields_to_clear = [col for col in column_names if col not in ['hbnb_number', 'record_content']]
            print(f"需要清除的字段: {fields_to_clear}")
            
            if fields_to_clear:
                # 构建UPDATE语句，将所有其他字段设置为NULL
                set_clause = ", ".join([f"{field} = NULL" for field in fields_to_clear])
                update_sql = f"UPDATE hbpr_full_records SET {set_clause}"
                
                print(f"执行SQL: {update_sql}")
                cursor.execute(update_sql)
                conn.commit()
                print(f"已清除 {len(fields_to_clear)} 个字段的数据，保留 {total_records} 条记录")
            else:
                print("没有需要清除的字段")
            
            conn.close()
            return True
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")





    def get_flight_info(self):
        """获取当前数据库的航班信息"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查是否存在flight_info表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='flight_info'")
            if not cursor.fetchone():
                conn.close()
                return None
            
            cursor.execute("SELECT flight_id, flight_number, flight_date FROM flight_info LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'flight_id': result[0],
                    'flight_number': result[1],
                    'flight_date': result[2]
                }
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def check_hbnb_exists(self, hbnb_number: int):
        """检查HBNB号码是否存在于数据库中（完整记录或简单记录）"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查完整记录
            cursor.execute("SELECT 1 FROM hbpr_full_records WHERE hbnb_number = ?", (hbnb_number,))
            full_exists = cursor.fetchone() is not None
            
            # 检查简单记录
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("SELECT 1 FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
                simple_exists = cursor.fetchone() is not None
            else:
                simple_exists = False
            
            conn.close()
            
            return {
                'exists': full_exists or simple_exists,
                'full_record': full_exists,
                'simple_record': simple_exists
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_simple_record(self, hbnb_number: int, record_line: str):
        """创建简单HBPR记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 确保hbpr_simple_records表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hbpr_simple_records (
                    hbnb_number INTEGER PRIMARY KEY,
                    record_line TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入简单记录
            cursor.execute(
                'INSERT OR REPLACE INTO hbpr_simple_records (hbnb_number, record_line) VALUES (?, ?)',
                (hbnb_number, record_line)
            )
            
            conn.commit()
            conn.close()
            
            print(f"Created simple record for HBNB {hbnb_number}")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_full_record(self, hbnb_number: int, record_content: str):
        """创建完整HBPR记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 插入完整记录
            cursor.execute(
                'INSERT OR REPLACE INTO hbpr_full_records (hbnb_number, record_content) VALUES (?, ?)',
                (hbnb_number, record_content)
            )
            
            # 如果存在简单记录，删除它
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
            
            conn.commit()
            conn.close()
            
            print(f"Created full record for HBNB {hbnb_number}")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def delete_simple_record(self, hbnb_number: int):
        """删除简单HBPR记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM hbpr_simple_records WHERE hbnb_number = ?", (hbnb_number,))
            
            conn.commit()
            conn.close()
            
            # 更新missing_numbers表
            try:
                self.update_missing_numbers_table()
                print(f"Updated missing numbers table after deleting HBNB {hbnb_number}")
            except Exception as e:
                print(f"Warning: Could not update missing numbers table: {e}")
            
            print(f"Deleted simple record for HBNB {hbnb_number}")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def extract_flight_info_from_hbpr(self, hbpr_content: str):
        """从HBPR内容中提取航班信息"""
        import re
        
        # 查找航班信息模式
        match = re.search(r'>HBPR:\s*([^*,]+)', hbpr_content)
        if match:
            flight_info = match.group(1).strip()
            # 解析航班号和日期
            if '/' in flight_info:
                parts = flight_info.split('/')
                if len(parts) >= 2:
                    flight_number = parts[0]
                    date = parts[1].split('*')[0] if '*' in parts[1] else parts[1]
                    return {
                        'flight_number': flight_number,
                        'flight_date': date,
                        'flight_info': flight_info
                    }
            
            return {
                'flight_number': flight_info,
                'flight_date': 'Unknown',
                'flight_info': flight_info
            }
        
        return None


    def extract_hbnb_from_simple_record(self, record_line: str):
        """从简单记录中提取HBNB号码"""
        import re
        
        # 格式: hbpr *,{NUMBER} 或 HBPR *,{NUMBER}
        match = re.search(r'hbpr\s*[^,]*,(\d+)', record_line, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None


    def is_simple_record(self, content: str):
        """判断是否为简单记录"""
        import re
        
        # 简单记录格式: hbpr *,{NUMBER} 或 HBPR *,{NUMBER}
        return bool(re.match(r'^hbpr\s*[^,]*,(\d+)$', content.strip(), re.IGNORECASE))


    def is_full_record(self, content: str):
        """判断是否为完整记录"""
        # 完整记录以 >HBPR: 开头
        return content.strip().startswith('>HBPR:')


    def validate_flight_info_match(self, hbpr_content: str):
        """验证HBPR内容中的航班信息是否与数据库匹配"""
        if not self.db_file:
            self.find_database()
        
        # 获取数据库中的航班信息
        db_flight_info = self.get_flight_info()
        if not db_flight_info:
            return {'match': False, 'reason': 'No flight info in database'}
        
        # 从HBPR内容中提取航班信息
        hbpr_flight_info = self.extract_flight_info_from_hbpr(hbpr_content)
        if not hbpr_flight_info:
            return {'match': False, 'reason': 'No flight info found in HBPR content'}
        
        # 比较航班信息
        db_flight_number = db_flight_info['flight_number']
        hbpr_flight_number = hbpr_flight_info['flight_number']
        
        if db_flight_number == hbpr_flight_number:
            return {
                'match': True,
                'db_flight': db_flight_info,
                'hbpr_flight': hbpr_flight_info
            }
        else:
            return {
                'match': False,
                'reason': f'Flight number mismatch: DB={db_flight_number}, HBPR={hbpr_flight_number}',
                'db_flight': db_flight_info,
                'hbpr_flight': hbpr_flight_info
            }


    def get_simple_records(self):
        """获取所有简单记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查是否存在hbpr_simple_records表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            cursor.execute("SELECT hbnb_number, record_line FROM hbpr_simple_records ORDER BY hbnb_number")
            results = cursor.fetchall()
            conn.close()
            
            return [{'hbnb_number': row[0], 'record_line': row[1]} for row in results]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def get_record_summary(self):
        """获取记录摘要信息"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 获取完整记录数量
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            full_count = cursor.fetchone()[0]
            
            # 获取简单记录数量
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hbpr_simple_records'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM hbpr_simple_records")
                simple_count = cursor.fetchone()[0]
            else:
                simple_count = 0
            
            # 获取已验证记录数量
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_validated = 1")
            validated_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'full_records': full_count,
                'simple_records': simple_count,
                'validated_records': validated_count,
                'total_records': full_count + simple_count
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


    def create_duplicate_record_table(self):
        """创建duplicate_record表"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 创建duplicate_record表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duplicate_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hbnb_number INTEGER NOT NULL,
                    original_hbnb_id INTEGER NOT NULL,
                    record_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (original_hbnb_id) REFERENCES hbpr_full_records(hbnb_number)
                )
            ''')
            
            conn.commit()
            conn.close()
            print("Created duplicate_record table")
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def create_duplicate_record(self, hbnb_number: int, original_hbnb_id: int, record_content: str):
        """创建重复记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            # 确保duplicate_record表存在
            self.create_duplicate_record_table()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 插入重复记录
            cursor.execute(
                'INSERT INTO duplicate_record (hbnb_number, original_hbnb_id, record_content) VALUES (?, ?, ?)',
                (hbnb_number, original_hbnb_id, record_content)
            )
            
            # 更新原始记录的bol_duplicate标志
            cursor.execute(
                'UPDATE hbpr_full_records SET bol_duplicate = 1 WHERE hbnb_number = ?',
                (original_hbnb_id,)
            )
            
            conn.commit()
            conn.close()
            
            print(f"Created duplicate record for HBNB {hbnb_number} (original: {original_hbnb_id})")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def create_duplicate_record_with_time(self, hbnb_number: int, original_hbnb_id: int, record_content: str, created_at: str):
        """创建重复记录并指定创建时间"""
        if not self.db_file:
            self.find_database()
        
        try:
            # 确保duplicate_record表存在
            self.create_duplicate_record_table()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 插入重复记录并指定创建时间
            cursor.execute(
                'INSERT INTO duplicate_record (hbnb_number, original_hbnb_id, record_content, created_at) VALUES (?, ?, ?, ?)',
                (hbnb_number, original_hbnb_id, record_content, created_at)
            )
            
            # 更新原始记录的bol_duplicate标志
            cursor.execute(
                'UPDATE hbpr_full_records SET bol_duplicate = 1 WHERE hbnb_number = ?',
                (original_hbnb_id,)
            )
            
            conn.commit()
            conn.close()
            
            print(f"Created duplicate record for HBNB {hbnb_number} (original: {original_hbnb_id}) with original timestamp")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_original_record_info(self, hbnb_number: int):
        """获取原始记录的内容和创建时间"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT record_content, created_at FROM hbpr_full_records WHERE hbnb_number = ?", 
                (hbnb_number,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'record_content': result[0],
                    'created_at': result[1]
                }
            else:
                return None
                
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def auto_backup_before_replace(self, hbnb_number: int):
        """在替换记录前自动备份原始记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            # 获取原始记录信息
            original_info = self.get_original_record_info(hbnb_number)
            
            if original_info:
                # 创建备份记录，保持原始创建时间
                self.create_duplicate_record_with_time(
                    hbnb_number, 
                    hbnb_number, 
                    original_info['record_content'], 
                    original_info['created_at']
                )
                return True
            else:
                return False
                
        except Exception as e:
            raise Exception(f"Auto backup failed: {e}")
    
    
    def get_duplicate_records(self, original_hbnb_id: int):
        """获取指定HBNB的所有重复记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查duplicate_record表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='duplicate_record'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            # 获取重复记录
            cursor.execute(
                'SELECT id, hbnb_number, record_content, created_at FROM duplicate_record WHERE original_hbnb_id = ? ORDER BY created_at',
                (original_hbnb_id,)
            )
            results = cursor.fetchall()
            conn.close()
            
            return [{'id': row[0], 'hbnb_number': row[1], 'record_content': row[2], 'created_at': row[3]} for row in results]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_all_duplicate_hbnbs(self):
        """获取所有有重复记录的HBNB号码"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 检查duplicate_record表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='duplicate_record'")
            if not cursor.fetchone():
                conn.close()
                return []
            
            # 获取所有有重复记录的HBNB号码
            cursor.execute(
                'SELECT DISTINCT original_hbnb_id FROM duplicate_record ORDER BY original_hbnb_id'
            )
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_duplicate_record_content(self, duplicate_id: int):
        """根据duplicate record ID获取记录内容"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT record_content FROM duplicate_record WHERE id = ?',
                (duplicate_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                raise ValueError(f"No duplicate record found with ID {duplicate_id}")
                
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_combined_records_for_display(self):
        """获取用于显示的组合记录（包括原始记录和重复记录）"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            records = []
            
            # 获取所有完整记录
            cursor.execute(
                'SELECT hbnb_number, record_content, created_at, bol_duplicate FROM hbpr_full_records ORDER BY hbnb_number'
            )
            full_records = cursor.fetchall()
            
            for record in full_records:
                hbnb_number, content, created_at, bol_duplicate = record
                records.append({
                    'type': 'original',
                    'hbnb_number': hbnb_number,
                    'record_content': content,
                    'created_at': created_at,
                    'has_duplicates': bool(bol_duplicate),
                    'duplicate_id': None
                })
                
                # 如果有重复记录，也添加进来
                if bol_duplicate:
                    duplicates = self.get_duplicate_records(hbnb_number)
                    for dup in duplicates:
                        records.append({
                            'type': 'duplicate',
                            'hbnb_number': dup['hbnb_number'],
                            'record_content': dup['record_content'],
                            'created_at': dup['created_at'],
                            'has_duplicates': False,
                            'duplicate_id': dup['id'],
                            'original_hbnb': hbnb_number
                        })
            
            conn.close()
            return records
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


def main():
    """测试__GetProperties方法"""
    with open("sample_hbpr.txt", "r", encoding="utf-8") as f:
        sample_content = f.read()
    
    chbpr = CHbpr()
    chbpr.run(sample_content)
    
    print("Debug Message:", chbpr.debug_msg)
    print("error_msg:", chbpr.error_msg)


if __name__ == "__main__":
    main() 