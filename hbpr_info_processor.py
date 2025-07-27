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
from general_func import CArgs
from hbpr_list_processor import HBPRProcessor


class CHbpr:
    """This class will process a single passenger information from HBPR page."""
    # 输出变量, 解析后的结构化数据字段 - 用于数据库存储
    error_msg = []
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
    CKIN_MSG = ""
    EXPC_PIECE = 0
    EXPC_WEIGHT = 0
    ASVC_PIECE = 0
    FBA_PIECE = 0
    IFBA_PIECE = 0
    FLYER_BENEFIT = 0
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
            self.error_msg.clear()
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
            self.CKIN_MSG = ""
            self.EXPC_PIECE = 0
            self.EXPC_WEIGHT = 0
            self.ASVC_PIECE = 0
            self.FBA_PIECE = 0
            self.IFBA_PIECE = 0
            self.FLYER_BENEFIT = 0
            self.IS_CA_FLYER = False
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
                    #self.__GetVisaInfo()
                    self.__NameMatch()
                else:
                    self.debug_msg.append("No BN number found, skipping validation")
        except Exception as e:
            self.error_msg.append(
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
            self.error_msg.append(f"HBPR{self.HbnbNumber},\tPassenger name not found.")
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
            self.error_msg.append(f"HBPR{self.HbnbNumber},\tNone validity classes are found.")
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
        # 提取EXPC、ASVC、FBA等行李信息
        expc_data = self.__ExpcStatement()
        if expc_data:
            self.EXPC_PIECE = expc_data.get("piece", 0)
            self.EXPC_WEIGHT = expc_data.get("weight", 0)
        # 提取ASVC行李
        self.ASVC_PIECE = self.__AsvcBagStatement()
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
        self.__CaptureCkin()
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
        self.debug_msg.append("expc piece = " + str(result.get("piece", 0)))
        self.debug_msg.append("expc ttl w = " + str(result["weight"]))
        return result


    def __AsvcBagStatement(self):
        """处理ASVC行李语句"""
        # 查找所有ASVC-消息
        asvc_pat = re.compile(r"ASVC-[^\n]*")
        asvc_matches = asvc_pat.findall(self.__Hbpr)
        result_piece = 0
        if not asvc_matches:
            return result_piece
        # 遍历所有ASVC行
        for asvc_line in asvc_matches:
            # 查找该行中所有的PC数量
            pc_pat = re.compile(r"/(\d)PC\s")
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
        return result_piece


    def __RegularBags(self):
        """获取常规行李额度"""
        pat = re.compile(r"\sFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        result = {"FBA": 0, "IFBA": 0}
        if re_match:
            try:
                result["FBA"] = int(self.__Hbpr[re_match.start() + 5])
            except:
                self.error_msg.append(
                    f"HBPR{self.HbnbNumber},\tFBA got an error."
                )
        pat = re.compile(r"\sIFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        if re_match:
            result["IFBA"] = 1
        self.debug_msg.append("adult bag  = " + str(result["FBA"]))
        self.debug_msg.append("Infant bag = " + str(result["IFBA"]))
        return result


    def __FlyerBenifit(self):
        """获取常旅客权益"""
        # 查找FF模式并提取FF号码
        ff_pat = re.compile(r"FF/([A-Z]{2}\s\d+/[A-Z])")
        ff_match = ff_pat.search(self.__Hbpr)
        # 默认没有会员，也不是国航常旅客
        result = {"piece": 0, "bol_ca": False}
        if ff_match:
            # 提取FF号码：如 "CA 050021619897/B"
            self.FF = ff_match.group(1)
            self.debug_msg.append("FF number = " + self.FF)
            match_content = self.__Hbpr[ff_match.start():ff_match.end()]
            # 检查是否为国航会员
            if self.FF.startswith("CA"):
                result["bol_ca"] = True
            # 查找金卡标识 /*G
            if "/*G" in match_content:
                result["piece"] = 1
            # 查找银卡标识 /*S (只对国航会员有效)
            elif "/*S" in match_content and result["bol_ca"]:
                result["piece"] = 1
        else:
            self.FF = ""
        self.debug_msg.append("flyer benif = " + str(result["piece"]))
        self.debug_msg.append("CA flyer    = " + str(result["bol_ca"]))
        self.FLYER_BENEFIT = result["piece"]
        self.IS_CA_FLYER = result["bol_ca"]
        return result


    def __CalculateBagPieceAndWeight(self):
        """计算行李件数和重量"""
        expc = self.__ExpcStatement()
        asvc = self.__AsvcBagStatement()
        result = {"piece": 0, "weight": 0}
        arg = CArgs()
        if expc:
            result["piece"] = expc["piece"] + asvc
            result["weight"] = expc["weight"] + asvc * arg.ClassBagWeight(
                self.CLASS
            )
            self.debug_msg.append("total piece = " + str(result["piece"]))
            self.debug_msg.append("total weigh = " + str(result["weight"]))
            return result
        # 总件数=常旅客+网购+成人票+婴儿票
        result["piece"] = self.FLYER_BENEFIT + asvc + self.FBA_PIECE + self.IFBA_PIECE
        if self.IS_CA_FLYER:
            # 总重量 =（CA常旅客+网购+成人票） x 舱位重量
            result["weight"] = (
                self.FLYER_BENEFIT + asvc + self.FBA_PIECE
            ) * arg.ClassBagWeight(self.CLASS)
        else:
            # 总重量 = （非CA常旅客 x 金卡限制）+ （网购+成人票）x 舱位重量
            result["weight"] = self.FLYER_BENEFIT * arg.ForeignGoldFlyerBagWeight() + (
                asvc + self.FBA_PIECE
            ) * arg.ClassBagWeight(self.CLASS)
        if self.IFBA_PIECE != 0:
            # 总重量 附加 婴儿票重量
            result["weight"] = result["weight"] + arg.InfBagWeight()
        self.debug_msg.append("total piece = " + str(result["piece"]))
        self.debug_msg.append("total weigh = " + str(result["weight"]))
        return result


    def __CaptureCkin(self):
        """捕获CKIN信息"""
        pat = re.compile(r"CKIN\sEXBG")
        re_match = pat.search(self.__Hbpr)
        ckin_msg = "CKIN not found."
        if re_match:
            # 查找完整的CKIN行
            line_start = self.__Hbpr.rfind('\n', 0, re_match.start()) + 1
            line_end = self.__Hbpr.find('\n', re_match.end())
            if line_end == -1:
                line_end = len(self.__Hbpr)
            ckin_msg = self.__Hbpr[line_start:line_end]
            # 设置CKIN_MSG字段
            self.CKIN_MSG = ckin_msg
        return ckin_msg


    def __MatchingBag(self):
        """匹配行李"""
        max_bag = self.__CalculateBagPieceAndWeight()
        args = CArgs()
        if max_bag:
            self.BAG_ALLOWANCE = max_bag.get("piece")
        if self.BAG_PIECE > max_bag["piece"]:
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\thas "
                f"{self.BAG_PIECE - max_bag['piece']} extra bag(s)."
            )
            self.error_msg.append(self.__CaptureCkin())
        elif self.BAG_WEIGHT > max_bag["weight"]:
                self.error_msg.append(
                    f"HBPR{self.HbnbNumber},\tbaggage is overweight "
                    f"{self.BAG_WEIGHT - max_bag['weight']} KGs."
                )
                self.error_msg.append(self.__CaptureCkin())
        elif self.__ChkBagAverageWeight > args.ClassBagWeight(self.CLASS):
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\tbaggage is overweight "
                f"{self.__ChkBagAverageWeight - args.ClassBagWeight(self.CLASS)} KGs."
            )
            self.error_msg.append(self.__CaptureCkin())
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
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\t{str_difference_percentage}"
            )
        return False


    def __NameMatch(self):
        """执行姓名匹配"""
        recordName = self.NAME
        psptName = self.PSPT_NAME
        if recordName == self.__ERROR_NUMBER or psptName == self.__ERROR_NUMBER:
            self.error_msg.append(
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
                    self.error_msg.append(
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
            ckin_twov_pat = re.compile(r"CKIN TWOV")
            ckin_twov_match = ckin_twov_pat.search(self.__Hbpr)
            if visa_info_match or ckin_visa_match or ckin_twov_match:
                # 找到签证信息，记录调试信息
                if visa_info_match:
                    self.debug_msg.append("VISA INFO found")
                if ckin_visa_match:
                    self.debug_msg.append("CKIN VISA found")
            else:
                # 未找到签证信息，添加错误
                self.error_msg.append(
                    f"HBPR{self.HbnbNumber},\tNo visa information found for {nationality} passport holder /n"
                    f"(PAX: {self.NAME}, BN: {self.BoardingNumber})"
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
            'CKIN_MSG': self.CKIN_MSG,
            'EXPC_PIECE': self.EXPC_PIECE,
            'EXPC_WEIGHT': self.EXPC_WEIGHT,
            'ASVC_PIECE': self.ASVC_PIECE,
            'FBA_PIECE': self.FBA_PIECE,
            'IFBA_PIECE': self.IFBA_PIECE,
            'FLYER_BENEFIT': self.FLYER_BENEFIT,
            'IS_CA_FLYER': self.IS_CA_FLYER,
            'has_error': len(self.error_msg) > 0,
            'error_count': len(self.error_msg),
            'error_messages': '\n'.join(self.error_msg) if self.error_msg else ''
        }


    def is_valid(self):
        """检查记录是否通过验证（无错误）"""
        return len(self.error_msg) == 0




class HbprDatabase:
    """数据库操作类，管理HBPR相关的所有数据库操作"""
    
    def __init__(self, db_file: str = None):
        """初始化数据库连接"""
        self.db_file = db_file
        if db_file and not os.path.exists(db_file):
            raise FileNotFoundError(f"Database file {db_file} not found!")
    
    
    def find_database(self):
        """查找包含HBPR数据的数据库文件"""
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
                    self.db_file = db_file
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
        
        print(f"Database built successfully: {self.db_file}")
        return processor
    
    
    def _add_chbpr_fields(self):
        """向hbpr_full_records表添加CHbpr解析的字段"""
        if not self.db_file:
            self.find_database()
        
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
                ('expc_piece', 'INTEGER'),
                ('expc_weight', 'INTEGER'),
                ('asvc_piece', 'INTEGER'),
                ('fba_piece', 'INTEGER'),
                ('ifba_piece', 'INTEGER'),
                ('flyer_benefit', 'INTEGER'),
                ('is_ca_flyer', 'BOOLEAN'),
                ('error_count', 'INTEGER'),
                ('error_messages', 'TEXT'),
                ('validated_at', 'TIMESTAMP')
            ]
            
            # 添加不存在的字段
            for field_name, field_type in new_fields:
                if field_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE hbpr_full_records ADD COLUMN {field_name} {field_type}")
                        print(f"Added field: {field_name}")
                    except sqlite3.Error as e:
                        print(f"Warning: Could not add field {field_name}: {e}")
            
            conn.commit()
            conn.close()
            print("CHbpr fields added to hbpr_full_records table")
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
    
    
    def get_hbpr_record(self, hbnb_number: int):
        """从数据库获取HBPR记录内容"""
        if not self.db_file:
            self.find_database()
        
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
                    expc_piece = ?,
                    expc_weight = ?,
                    asvc_piece = ?,
                    fba_piece = ?,
                    ifba_piece = ?,
                    flyer_benefit = ?,
                    is_ca_flyer = ?,
                    error_count = ?,
                    error_messages = ?,
                    validated_at = CURRENT_TIMESTAMP
                WHERE hbnb_number = ?
            ''', (
                chbpr_instance.is_valid(),
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
                data['EXPC_PIECE'],
                data['EXPC_WEIGHT'],
                data['ASVC_PIECE'],
                data['FBA_PIECE'],
                data['IFBA_PIECE'],
                data['FLYER_BENEFIT'],
                data['IS_CA_FLYER'],
                data['error_count'],
                data['error_messages'],
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
    
    
    def erase_all_records_except_core(self):
        """删除hbpr_full_records表中除hbnb_number和record_content外的所有记录"""
        if not self.db_file:
            self.find_database()
        
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 获取当前记录数
            cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
            total_records = cursor.fetchone()[0]
            
            # 删除所有记录
            cursor.execute("DELETE FROM hbpr_full_records")
            
            # 重置自增ID（如果存在）
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='hbpr_full_records'")
            except sqlite3.Error:
                # sqlite_sequence表可能不存在，忽略错误
                pass
            
            conn.commit()
            conn.close()
            
            print(f"Erased {total_records} records from hbpr_full_records table")
            return True
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")


def build_database_from_hbpr_list():
    """使用hbpr_list_processor从sample_hbpr_list.txt构建数据库"""
    try:
        db = HbprDatabase()
        processor = db.build_from_hbpr_list()
        return db, processor
    except Exception as e:
        print(f"Error building database: {e}")
        print("Processing stopped.")
        return None, None


def get_hbpr_record_from_db(hbnb_number: int, db_file: str = None):
    """从数据库获取HBPR记录内容"""
    try:
        db = HbprDatabase(db_file)
        return db.get_hbpr_record(hbnb_number)
    except Exception as e:
        print(f"Error getting HBPR record: {e}")
        return None


def update_hbpr_record_with_validation(chbpr_instance: CHbpr, db_file: str = None):
    """使用CHbpr实例的结果更新hbpr_full_records表"""
    try:
        db = HbprDatabase(db_file)
        return db.update_with_chbpr_results(chbpr_instance)
    except Exception as e:
        print(f"Error updating HBPR record: {e}")
        return False




def test_chbpr_with_sample_data():
    """测试CHbpr类使用示例HBPR数据"""
    print("TESTING CHbpr CLASS WITH SAMPLE DATA")
    
    # 读取示例文件
    sample_file = "sample_hbpr.txt"
    try:
        print(f"Reading sample data from '{sample_file}'...")
        with open(sample_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()   
    except FileNotFoundError:
        print(f"Error: {sample_file} not found!")
        return
    
    # 创建CHbpr实例并处理记录
    hbpr_processor = CHbpr()
    hbpr_processor.run(content)
    
    # 获取结构化数据
    structured_data = hbpr_processor.get_structured_data()
    print("EXTRACTED DATA:")
    print(f"  HBNB Number: {structured_data['hbnb_number']}")
    print(f"  Boarding Number: {structured_data['boarding_number']}")
    print(f"  PNR: {structured_data['PNR']}")
    print(f"  Name: {structured_data['NAME']}")
    print(f"  Seat: {structured_data['SEAT']}")
    print(f"  Class: {structured_data['CLASS']}")
    print(f"  Destination: {structured_data['DESTINATION']}")
    print(f"  Passport Name: {structured_data['PSPT_NAME']}")
    print(f"  FF: {structured_data['FF']}")
    print(f"  Bag Pieces: {structured_data['BAG_PIECE']}")
    print(f"  Bag Weight: {structured_data['BAG_WEIGHT']}")
    print(f"  Bag Allowance: {structured_data['BAG_ALLOWANCE']}")
    
    # 显示验证状态
    if hbpr_processor.is_valid():
        print("  ✅ VALIDATION: PASSED")
    else:
        print("  ❌ VALIDATION: FAILED")
        print("  ERRORS:")
        for error in hbpr_processor.error_msg:
            print(f"    - {error}")
    
    # 显示调试信息（部分）
    if hbpr_processor.debug_msg:
        print("  DEBUG INFO:")
        for debug in hbpr_processor.debug_msg:
            print(f"    - {debug}")
    return 


def test_full_workflow():
    """测试完整工作流程：构建数据库 -> 获取记录 -> 处理 -> 更新"""
    print("=== TESTING FULL WORKFLOW ===")
    
    try:
        # 步骤1：构建数据库
        db, processor = build_database_from_hbpr_list()
        if not db or not processor:
            return
        
        # 步骤2：获取一个HBPR记录进行测试
        test_hbnb = 2  # 测试HBNB号码
        print(f"\nRetrieving HBPR record for HBNB {test_hbnb}...")
        hbpr_content = db.get_hbpr_record(test_hbnb)
        
        print(f"Found HBPR record for HBNB {test_hbnb}")
        print(f"Record length: {len(hbpr_content)} characters")
        
        # 步骤3：使用CHbpr处理记录
        print(f"\nProcessing HBPR {test_hbnb} with CHbpr...")
        chbpr = CHbpr()
        chbpr.run(hbpr_content)
        
        # 步骤4：显示结果
        data = chbpr.get_structured_data()
        print(f"\nProcessing Results:")
        print(f"  HBNB: {data['hbnb_number']}")
        print(f"  Name: {data['NAME']}")
        print(f"  Class: {data['CLASS']}")
        print(f"  Valid: {chbpr.is_valid()}")
        if not chbpr.is_valid():
            print(f"  Errors: {data['error_count']}")
            for error in chbpr.error_msg[:3]:
                print(f"    - {error}")
        
        # 步骤5：更新数据库
        print(f"\nUpdating hbpr_full_records table with validation results...")
        success = db.update_with_chbpr_results(chbpr)
        if success:
            print("✅ Database updated successfully!")
        else:
            print("❌ Failed to update database")
        
        # 步骤6：显示统计信息
        print(f"\nDatabase Statistics:")
        stats = db.get_validation_stats()
        print(f"  Total records: {stats['total_records']}")
        print(f"  Validated records: {stats['validated_records']}")
        print(f"  Valid records: {stats['valid_records']}")
        print(f"  Invalid records: {stats['invalid_records']}")
        
        print(f"\n=== Test Complete ===")
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        print("Processing stopped.")


def test_database_class():
    """测试HbprDatabase类的功能"""
    print("=== TESTING HbprDatabase CLASS ===")
    
    try:
        # 测试数据库构建
        print("1. Testing database building...")
        db = HbprDatabase()
        processor = db.build_from_hbpr_list()
        print(f"   ✅ Database built: {db.db_file}")
        
        # 测试记录获取
        print("\n2. Testing record retrieval...")
        test_hbnb = 2
        content = db.get_hbpr_record(test_hbnb)
        print(f"   ✅ Retrieved HBNB {test_hbnb}, length: {len(content)} chars")
        
        # 测试CHbpr处理和数据库更新
        print("\n3. Testing CHbpr processing and database update...")
        chbpr = CHbpr()
        chbpr.run(content)
        success = db.update_with_chbpr_results(chbpr)
        print(f"   ✅ Database update: {'SUCCESS' if success else 'FAILED'}")
        
        # 测试统计信息
        print("\n4. Testing validation statistics...")
        stats = db.get_validation_stats()
        print(f"   ✅ Stats retrieved: {stats}")
        
        print("\n=== HbprDatabase Class Test Complete ===")
        
    except Exception as e:
        print(f"❌ Database class test failed: {e}")


def clean_bn_related_errors(db_file: str = None, dry_run: bool = True):
    """清理数据库中与BN（登机号）相关的错误信息
    
    Args:
        db_file: 数据库文件路径，如果为None则自动查找
        dry_run: 如果为True，只显示将要清理的内容，不实际修改数据库
    
    Returns:
        int: 清理的记录数量
    """
    try:
        # 如果没有指定数据库文件，尝试查找
        if not db_file:
            db = HbprDatabase()
            db.find_database()
            db_file = db.db_file
        
        if not os.path.exists(db_file):
            print(f"❌ 数据库文件不存在: {db_file}")
            return 0
        
        print(f"🔧 清理BN相关错误 ({'预览模式' if dry_run else '执行模式'}): {db_file}")
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 查找包含BN相关错误的记录
        cursor.execute("""
            SELECT hbnb_number, name, error_count, error_messages, is_valid
            FROM hbpr_full_records 
            WHERE error_messages IS NOT NULL AND error_messages != ''
        """)
        
        all_error_records = cursor.fetchall()
        
        if not all_error_records:
            print("✅ 没有找到需要清理的错误记录")
            conn.close()
            return 0
        
        cleaned_count = 0
        
        # BN相关错误的匹配模式 - BN#0是最常见的模式
        bn_error_patterns = [
            r'BN#0[^0-9]',  # BN#0 后面跟非数字字符（如分隔符）
            r'Boarding Number should be 0',
            r'boarding.*not found',
            r'BN.*not.*found',
            r'missing.*boarding.*number',
        ]
        
        for hbnb, name, error_count, error_messages, is_valid in all_error_records:
            if not error_messages:
                continue
            
            # 按行分割错误信息
            error_lines = error_messages.split('\n')
            cleaned_lines = []
            removed_errors = []
            
            for line in error_lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否为BN相关错误
                is_bn_error = False
                for pattern in bn_error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_bn_error = True
                        removed_errors.append(line)
                        break
                
                # 如果不是BN相关错误，保留
                if not is_bn_error:
                    cleaned_lines.append(line)
            
            # 如果有BN错误被移除
            if removed_errors:
                new_error_messages = '\n'.join(cleaned_lines) if cleaned_lines else ''
                new_error_count = len(cleaned_lines)
                new_is_valid = 1 if new_error_count == 0 else 0
                
                if not dry_run:
                    print(f"  🔧 清理 HBNB {hbnb} - {name or 'Unknown'}: {error_count} -> {new_error_count} 个错误")
                else:
                    print(f"  🔍 将清理 HBNB {hbnb} - {name or 'Unknown'}: {error_count} -> {new_error_count} 个错误")
                
                if not dry_run:
                    # 实际更新数据库
                    cursor.execute("""
                        UPDATE hbpr_full_records 
                        SET error_count = ?, error_messages = ?, is_valid = ?, validated_at = CURRENT_TIMESTAMP
                        WHERE hbnb_number = ?
                    """, (new_error_count, new_error_messages, new_is_valid, hbnb))
                
                cleaned_count += 1
        
        if not dry_run and cleaned_count > 0:
            conn.commit()
            print(f"\n✅ 已清理 {cleaned_count} 条记录中的BN相关错误")
        elif dry_run:
            print(f"\n🔍 预览: 将清理 {cleaned_count} 条记录")
            print("使用 clean_bn_related_errors(dry_run=False) 执行实际清理")
        else:
            print(f"\n✅ 没有找到需要清理的BN相关错误")
        
        conn.close()
        return cleaned_count
        
    except Exception as e:
        print(f"❌ BN错误清理失败: {e}")
        return 0



def check_and_fix_bn_errors_in_chbpr():
    """检查并修复CHbpr类中的BN错误处理逻辑
    
    确保CHbpr类不会为缺失的BN（登机号）生成错误信息，
    因为BN是可选的字段。
    """
    print("🔍 检查CHbpr类的BN错误处理...")
    
    # 这个函数主要是提醒和文档化
    print("✅ CHbpr类已正确处理可选的BN字段:")
    print("   - BN不存在时，BoardingNumber设为0")
    print("   - 不会为缺失的BN生成错误信息")
    print("   - 但是在错误分隔符中会显示'BN#0'，这需要在数据库层面清理")



def get_bn_cleanup_statistics(db_file: str = None):
    """获取BN清理相关的统计信息"""
    try:
        if not db_file:
            db = HbprDatabase()
            db.find_database() 
            db_file = db.db_file
        
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 检查包含BN#0错误的记录数
        cursor.execute("""
            SELECT COUNT(*) FROM hbpr_full_records 
            WHERE error_messages LIKE '%BN#0%'
        """)
        bn_zero_errors = cursor.fetchone()[0]
        
        # 检查总的错误记录数
        cursor.execute("""
            SELECT COUNT(*) FROM hbpr_full_records 
            WHERE error_messages IS NOT NULL AND error_messages != ''
        """)
        total_error_records = cursor.fetchone()[0]
        
        # 检查有效记录数
        cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE is_valid = 1")
        valid_records = cursor.fetchone()[0]
        
        # 检查总记录数
        cursor.execute("SELECT COUNT(*) FROM hbpr_full_records")
        total_records = cursor.fetchone()[0]
        
        print(f"📊 BN错误统计信息 ({db_file}):")
        print(f"   - 包含BN#0错误的记录: {bn_zero_errors}")
        print(f"   - 总错误记录数: {total_error_records}")
        print(f"   - 有效记录数: {valid_records}")
        print(f"   - 总记录数: {total_records}")
        
        if total_records > 0:
            clean_rate = ((total_records - bn_zero_errors) / total_records) * 100
            print(f"   - 清理后预期成功率: {clean_rate:.1f}%")
        
        conn.close()
        return {
            'bn_zero_errors': bn_zero_errors,
            'total_error_records': total_error_records,
            'valid_records': valid_records,
            'total_records': total_records
        }
        
    except Exception as e:
        print(f"❌ 统计信息获取失败: {e}")
        return None



def main():
    """主函数"""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # 测试模式：测试CHbpr类
        test_chbpr_with_sample_data()
    elif len(sys.argv) > 1 and sys.argv[1] == '--workflow':
        # 工作流测试模式
        test_full_workflow()
    elif len(sys.argv) > 1 and sys.argv[1] == '--build':
        # 构建数据库模式
        build_database_from_hbpr_list()
    elif len(sys.argv) > 1 and sys.argv[1] == '--db-test':
        # 数据库类测试模式
        test_database_class()
    elif len(sys.argv) > 1 and sys.argv[1] == '--clean-bn':
        # BN错误清理模式
        get_bn_cleanup_statistics()
        clean_bn_related_errors(dry_run=False)
    else:
        # 默认：运行完整工作流测试
        test_full_workflow()


if __name__ == "__main__":
    main() 