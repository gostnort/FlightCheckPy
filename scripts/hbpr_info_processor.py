#!/usr/bin/env python3
"""
HBPR Information Processor
Processes HBPR passenger records and validates/stores results.
"""

import re
import datetime
import sqlite3
import os
import time
from typing import Any, Optional
from .general_func import CArgs
from .data_cleaner import clean_hbpr_record_content
import pandas as pd


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
    ASVC_SEAT = ""
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
    TKNE = ""  # Add TKNE field
    HAS_INFANT = False
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
            self.ASVC_SEAT = ""
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
            self.TKNE = ""  # Initialize TKNE field
            self.HAS_INFANT = False
            # 调用处理方法
            bolRun = True
            # 首先获取HBNB号码（用于错误消息）
            bolRun = self.__GetHbnbNumber()
            if bolRun:
                # 然后获取乘客信息（姓名、登机号、座位、舱位、目的地）
                bolRun = self.__GetPassengerInfo()
            if bolRun:
                self.__ExtractStructuredData()  # 新方法：提取结构化数据
                # 检测婴儿
                self.__DetectInfant()
                # 检查是否有BN号码，如果没有则跳过验证
                if self.BoardingNumber > 0:
                    self.__MatchingBag()
                    self.__GetPassportExp()
                    self.__GetVisaInfo()
                    self.__NameMatch()
                    self.__GetProperties()
                    self.__GetConnectingFlights()
                else:
                    self.__GetProperties()
                    self.__GetConnectingFlights()
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
        hbnbPat = re.compile(r">?HBPR:\s*[^,]+,(\d+)")
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
        # 提取ASVC消息和座位信息（独立的早期提取，不依赖登机号）
        self.__CaptureAsvcMessages()
        return


    def __DetectInfant(self):
        """检测是否有婴儿信息（以"INF-"开头的行）"""
        try:
            # 优先依据以 INF- 开头的行
            if re.search(r"^\s*INF-", self.__Hbpr, flags=re.MULTILINE):
                self.HAS_INFANT = True
                return True
            # 兼容性：若出现 IFBA/ 或文中有 INF1/ 等标识，也认为随行婴儿存在
            if re.search(r"\bIFBA/\dPC\b", self.__Hbpr) or re.search(r"\bINF\d/", self.__Hbpr):
                self.HAS_INFANT = True
                return True
        except Exception:
            pass
        self.HAS_INFANT = False
        return False


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
        """处理ASVC行李语句（只计算行李件数，ASVC_MSG已在__CaptureAsvcMessages中填充）"""
        # 使用已填充的ASVC_MSG列表
        result_piece = 0
        if not self.ASVC_MSG:
            return result_piece
        # 遍历所有ASVC行查找PC数量
        for asvc_line in self.ASVC_MSG:
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
        result = {"FBA": 1, "IFBA": 0} # 默认有1件FBA
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
        ff_pat = re.compile(r"FF/([A-Z]{2}\s?[A-Z0-9]+(?:/[A-Z])?(?:/\*[GS])?)")
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
        pat = re.compile(r"\nCKIN\s+[^\n]*")
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


    def __CaptureAsvcMessages(self):
        """
        捕获ASVC消息，并设置ASVC_MSG字段
        搜索所有以'ASVC-'开头的行
        如果ASVC信息不存在，则设置ASVC_MSG字段为"ASVC not found."
        只返回ASVC消息,如果有的话。
        """
        # 清空之前的ASVC_MSG列表
        self.ASVC_MSG.clear()
        # 使用findall来找到所有匹配的ASVC行
        pat = re.compile(r"\nASVC-[^\n]*")
        re_matches = pat.findall(self.__Hbpr)
        if re_matches:
            # 将所有找到的ASVC行添加到列表中
            for match in re_matches:
                self.ASVC_MSG.append(match.strip())
        else:
            #self.ASVC_MSG.append("ASVC not found.")
            return "ASVC not found."
        # 提取ASVC座位信息（必须在ASVC_MSG被填充后调用）
        self.__GetAsvcSeat()
        return


    def __GetAsvcSeat(self):
        """获取ASVC座位信息
        从已填充的ASVC_MSG列表中提取座位号
        匹配格式: SEAT/[format_char] [seat_number]，例如 SEAT/E 47L
        """
        if not self.ASVC_MSG:
            return
        # 遍历ASVC_MSG列表查找座位信息
        for asvc_msg in self.ASVC_MSG:
            if "SEAT" in asvc_msg:
                # 匹配格式: SEAT/[format_char] [seat_number]
                # 例如: ASVC- A/0B5/SEAT/E 47L CNY1000 A/EMDA-9994565054384/1
                seat_match = re.search(r"SEAT/[A-Z]\s(\d{1,2}[A-Z])", asvc_msg)
                if seat_match:
                    self.ASVC_SEAT = seat_match.group(1)
                    self.debug_msg.append(f"ASVC seat found: {self.ASVC_SEAT}")
                    return


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
        elif max_bag["piece"] > 0 and self.__ChkBagAverageWeight > (max_bag["weight"] / max_bag["piece"]):
            if self.__ChkBagAverageWeight > args.ClassBagWeight(self.CLASS):
                if self.BAG_WEIGHT > self.EXPC_WEIGHT:
                    avg_allowance = max_bag["weight"] / max_bag["piece"] if max_bag["piece"] > 0 else 0
                    self.error_msg["Baggage"].append(
                        f"HBPR{self.HbnbNumber},the baggage average weight is overweight "
                        f"{self.__ChkBagAverageWeight - avg_allowance} KGs."
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
        # 防止除零错误
        if max_length == 0:
            # 如果两个字符串都为空，认为匹配
            return True
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
            'ASVC_SEAT': self.ASVC_SEAT,
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
            'TKNE': self.TKNE,  # Add TKNE to structured data
            'HAS_INFANT': self.HAS_INFANT,
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
        # 提取TKNE数据
        self.ExtractTKNE(properties)
        # 删除特定的属性（其他筛选交给UI层处理）
        properties_to_remove = []
        for property in properties:
            if any([
                len(property) == 1,  # 删除舱位
                property.startswith("R"),  # 删除座位
                property.startswith("SNR"),  # 删除SNR的座位
                property.startswith("FF/"),  # 删除FF属性（保留会员号）
                property.startswith("FR/"),  # 删除FR属性（保留会员号）
            ]):
                properties_to_remove.append(property)
        # 删除不需要的属性
        for property in properties_to_remove:
            if property in properties:
                if property.startswith("FF/"):  # FF号码后面一个属性是FF的会员号
                    index = properties.index(property)
                    properties.remove(property)
                    properties.remove(properties[index])  # 紧跟其后的FF会员号会马上替代原来的index
                    continue
                elif property.startswith("FR/"):  # FR号码后面一个属性是FR的会员号
                    index = properties.index(property)
                    properties.remove(property)
                    properties.remove(properties[index])  # 紧跟其后的FR会员号会马上替代原来的index
                    continue
                else:
                    properties.remove(property)
        self.PROPERTIES = properties
        return


    def ExtractTKNE(self, properties):
        """提取TKNE数据"""
        for i, property in enumerate(properties):
            if property.startswith("TKNE/"):
                # Extract the numbers following TKNE/
                tkne_part = property[5:]  # Remove "TKNE/" prefix
                # Split by '/' and take the first part (13+ digits) and second part (1 digit)
                parts = tkne_part.split('/')
                if len(parts) >= 2:
                    # Combine the parts: first part + '/' + second part
                    self.TKNE = f"{parts[0]}/{parts[1]}"
                    self.debug_msg.append(f"TKNE extracted: {self.TKNE}")
                else:
                    # If format is different, store as is
                    self.TKNE = tkne_part
                    self.debug_msg.append(f"TKNE extracted (alternative format): {self.TKNE}")
                break


    def is_valid(self):
        """检查记录是否通过验证（无错误）"""
        return not any(self.error_msg.values())


def main():
    """主函数 - 现在作为一个示例，展示如何使用该模块中的类"""
    print("🧹 HBPR Info Processor Tool")
    print("=" * 50)
    print("该脚本现在应该作为模块导入，而不是直接运行。")
    print("用法示例:")
    print("  from scripts.hbpr_info_processor import CHbpr")
    print("  from scripts.hbpr_database import HbprDatabase")
    print("  from ui.common import get_hbpr_database_client # Assuming UI is running")
    print("")
    print("  # 1. Get database client")
    print("  db_client = get_hbpr_database_client()")
    print("  if db_client:")
    print("      # 2. Get a specific record")
    print("      record_content = db_client.get_hbpr_record(hbnb_number=123)")
    print("")
    print("      # 3. Process it with CHbpr")
    print("      processor = CHbpr()")
    print("      processor.run(record_content)")
    print("")
    print("      # 4. Update the database with results")
    print("      db_client.update_with_chbpr_results(processor)")


if __name__ == "__main__":
    main()

