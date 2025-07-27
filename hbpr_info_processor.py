#!/usr/bin/env python3
"""
HBPR Information Processor
Processes HBPR passenger records similar to obtain_info.py for PR records.
Extracts passenger information, performs validations, and stores results.
"""

import re
import datetime
import sqlite3
import os
from general_func import CArgs


class CHbpr:
    """This class will process a single passenger information from HBPR page."""

    # 输出变量
    error_msg = []
    BoardingNumber = 0
    HbnbNumber = 0
    debug_msg = []

    # 私有变量
    __ChkBagAverageWeight = 0
    __ChkBagPcs = 0
    __ChkBagTtlWeight = 0
    __MainCls = ""
    __ERROR_NUMBER = 65535
    __SEPARATED_BAR = "__________________________________"
    __BolError = False


    def __init__(self):
        super().__init__()


    def run(self, HbprContent: str):
        """处理HBPR记录的主要方法"""
        try:
            # 初始化所有类级变量
            self.debug_msg.clear()
            self.debug_msg.append(self.__SEPARATED_BAR)
            self.error_msg.clear()
            self.BoardingNumber = 0
            self.HbnbNumber = 0
            self.__ChkBagAverageWeight = 0
            self.__ChkBagPcs = 0
            self.__Hbpr = HbprContent
            self.__BolError = False
            # 调用处理方法
            bolRun = True
            bolRun = self.__GetBnAndCls()
            if bolRun:
                self.__GetChkBag()
                self.__MatchingBag()
                self.__GetPassportExp()
                self.__NameMatch()
            # 如果有错误，添加分隔符
            if self.__BolError:
                self.error_msg.append('BN#' + str(self.BoardingNumber) + self.__SEPARATED_BAR + '\n')
        except Exception as e:
            self.error_msg.append(
                f"A Fatal Error occurred at HBPR{self.HbnbNumber}; "
                f"Boarding Number should be {self.BoardingNumber}. Error: {str(e)}"
            )


    def __del__(self):
        self.debug_msg.append(
            f"Boarding number {self.BoardingNumber}. \nCHbpr deconstruction."
        )


    def __GetBnAndCls(self):
        """获取登机号和舱位"""
        # 搜索登机号
        bnPat = re.compile(r"BN\d{3}(\s{1,2}|\s\*)(\*?\w)")  # 乘客可能已登机
        bnMatch = bnPat.search(self.__Hbpr)
        if bnMatch:
            try:
                bnIndex = bnMatch.start() + 2
                self.BoardingNumber = int(self.__Hbpr[bnIndex : bnIndex + 3])
                self.debug_msg.append("boarding # = " + str(self.BoardingNumber))
            except:
                self.BoardingNumber = self.__ERROR_NUMBER
        # 搜索子舱位并转换为主舱位
        clsPat = re.compile(r"\s{2}[A-Z]\s{1}")
        try:
            clsIndex = clsPat.search(self.__Hbpr, bnIndex, bnIndex + 20).start() + 2
            self.__MainCls = self.__Hbpr[clsIndex]
        except:
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\tNone validity classes are found."
            )
            self.__BolError = True
            return False
        fltArgs = CArgs()
        self.__MainCls = fltArgs.SubCls2MainCls(self.__MainCls)
        self.debug_msg.append("main class = " + self.__MainCls)
        # 搜索HBNB号码（从标题行提取）
        hbnbPat = re.compile(r">HBPR:\s*[^,]+,(\d+)")
        hbnbMatch = hbnbPat.search(self.__Hbpr)
        if hbnbMatch:
            try:
                self.HbnbNumber = int(hbnbMatch.group(1))
                self.debug_msg.append("HBNB number = " + str(self.HbnbNumber))
            except:
                self.HbnbNumber = self.__ERROR_NUMBER
        return True


    def __GetChkBag(self):
        """获取托运行李信息"""
        bagCount = 0
        bagWeight = 0
        # HBPR格式中行李信息可能不同，这里简化处理
        # 如果没有明确的行李标签，设为默认值
        self.__ChkBagPcs = bagCount
        self.__ChkBagTtlWeight = bagWeight
        if bagCount == 0:
            self.__ChkBagAverageWeight = 0
        else:
            self.__ChkBagAverageWeight = bagWeight / bagCount
        self.debug_msg.append("bag piece  = " + str(self.__ChkBagPcs))
        self.debug_msg.append("bag total w= " + str(self.__ChkBagTtlWeight))
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


    def __AsvcBagStatement(self, StartIndex=1):
        """处理ASVC行李语句"""
        pat = re.compile(r"ASVC-\s")
        re_match = pat.search(self.__Hbpr, StartIndex)
        result = {}
        if re_match is None:
            return result
        else:
            result["index"] = re_match.end()
            result["piece"] = 0
        pat = re.compile(r"XBAG/")
        re_match = pat.search(self.__Hbpr, result["index"])
        if re_match:
            return result
        pat = re.compile(r"/\dPC\s")
        re_match = pat.search(self.__Hbpr, result["index"])
        if re_match:
            try:
                result["piece"] = int(self.__Hbpr[re_match.start() + 1])
                result["index"] = re_match.end()
                self.debug_msg.append("asvc bag p = " + str(result["piece"]))
            except:
                self.debug_msg.append("asvc bag p type error")
        return result


    def __RegularBags(self):
        """获取常规行李额度"""
        pat = re.compile(r"\sFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        result = {"FBA": 2, "IFBA": 0}
        if re_match:
            try:
                result["FBA"] = int(self.__Hbpr[re_match.start() + 5])
            except:
                self.error_msg.append(
                    f"HBPR{self.HbnbNumber},\tFBA got an error. Set default as 2 pieces."
                )
                self.__BolError = True
        pat = re.compile(r"\sIFBA/\dPC")
        re_match = pat.search(self.__Hbpr)
        if re_match:
            result["IFBA"] = 1
        self.debug_msg.append("adult bag  = " + str(result["FBA"]))
        self.debug_msg.append("Infant bag = " + str(result["IFBA"]))
        return result


    def __FlyerBenifit(self):
        """获取常旅客权益"""
        pat = re.compile(r"\sFF/.")
        re_match = pat.search(self.__Hbpr)
        # 默认没有会员，也不是国航常旅客
        result = {"piece": 0, "bol_ca": False}
        if re_match:
            if self.__Hbpr[re_match.end()-1 : re_match.end() + 1] == "CA":
                result["bol_ca"] = True
        else:
            return result
        pat = re.compile(r"/\*G\s")
        re_match = pat.search(self.__Hbpr)
        # 如果是金卡，都有会员优惠
        if re_match:
            result["piece"] = 1
        pat = re.compile(r"/\*S\s")
        re_match = pat.search(self.__Hbpr)
        # 如果是银卡的国航会员，才有优惠
        if re_match and result["bol_ca"]:
            result["piece"] = 1
        self.debug_msg.append("flyer benif = " + str(result["piece"]))
        self.debug_msg.append("CA flyer    = " + str(result["bol_ca"]))
        return result


    def __CalculateBagPieceAndWeight(self):
        """计算行李件数和重量"""
        expc = self.__ExpcStatement()
        index = 1
        asvc_tmp = {}
        asvc = 0  # 因为ASVC结果需要累积
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
            result["weight"] = flyer["piece"] * arg.ForeignGoldFlyerBagWeight() + (
                asvc + regular["FBA"]
            ) * arg.ClassBagWeight(self.__MainCls)
        if regular["IFBA"] != 0:
            # 总重量 附加 婴儿票重量
            result["weight"] = result["weight"] + arg.InfBagWeight()
        self.debug_msg.append("total piece = " + str(result["piece"]))
        self.debug_msg.append("total weigh = " + str(result["weight"]))
        return result


    def __CaptureCkin(self):
        """捕获CKIN信息"""
        pat = re.compile(r"CKIN\s")
        re_match = pat.search(self.__Hbpr)
        ckin_msg = "CKIN not found."
        if re_match:
            # 查找完整的CKIN行
            line_start = self.__Hbpr.rfind('\n', 0, re_match.start()) + 1
            line_end = self.__Hbpr.find('\n', re_match.end())
            if line_end == -1:
                line_end = len(self.__Hbpr)
            ckin_msg = self.__Hbpr[line_start:line_end]
        return ckin_msg


    def __MatchingBag(self):
        """匹配行李"""
        max_bag = self.__CalculateBagPieceAndWeight()
        if self.__ChkBagPcs > max_bag["piece"]:
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\thas "
                f"{self.__ChkBagPcs - max_bag['piece']} extra bag(s)."
            )
            self.error_msg.append(self.__CaptureCkin())
            self.__BolError = True
        else:
            if self.__ChkBagTtlWeight > max_bag["weight"]:
                self.error_msg.append(
                    f"HBPR{self.HbnbNumber},\tbaggage is overweight "
                    f"{self.__ChkBagTtlWeight - max_bag['weight']} KGs."
                )
                self.error_msg.append(self.__CaptureCkin())
                self.__BolError = True
        return


    def __GetName(self):
        """获取乘客姓名"""
        try:
            namePat = re.compile(r"\d\.\s[A-Z/+\s]{3,17}")
            paxName = namePat.search(self.__Hbpr).group(0)
            paxName = paxName[3:]
            paxName = paxName.strip()
            self.debug_msg.append("pax name  = " + paxName)
        except:
            paxName = self.__ERROR_NUMBER
        return paxName


    def __PsptName(self):
        """获取护照姓名"""
        try:
            namePat = re.compile(r"PAXLST\s*:[A-Z/]{3,}\s")
            paxName = namePat.search(self.__Hbpr).group(0)
            paxName = paxName.strip()
            paxName = paxName[7:].strip().rstrip('/')
            self.debug_msg.append("pspt name = " + paxName)
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
            self.__BolError = True
        return False


    def __NameMatch(self):
        """执行姓名匹配"""
        recordName = self.__GetName()
        psptName = self.__PsptName()
        if recordName == self.__ERROR_NUMBER or psptName == self.__ERROR_NUMBER:
            self.error_msg.append(
                f"HBPR{self.HbnbNumber},\tPAX name not found."
            )
            self.__BolError = True
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
                nextDate = datetime.datetime.now()
                deltaT = datetime.timedelta(days=1)
                nextDate = nextDate + deltaT
                if nextDate > expDate:
                    errMsg = f"The passport expired on {expDate.strftime('%d%b%Y')}."
                    self.error_msg.append(
                        f"HBPR{self.HbnbNumber},\t{errMsg}"
                    )
                    self.__BolError = True
        except Exception as e:
            self.debug_msg.append(f"Passport expiration check failed: {str(e)}")


class HbprRecordParser:
    """HBPR记录解析器，将HBPR记录解析为结构化字段"""


    def __init__(self, db_file: str = "CA984_25JUL25.db"):
        """初始化解析器"""
        self.db_file = db_file
        self.parsed_results = []


    def parse_record(self, hbnb_number: int, record_content: str) -> dict:
        """
        解析单个HBPR记录
        Args:
            hbnb_number: HBNB号码
            record_content: 记录内容
        Returns:
            解析后的字段字典
        """
        result = {
            'hbnb_number': hbnb_number,
            'PNR': '',
            'NAME': '',
            'BN': '',
            'SEAT': '',
            'EXTRA_SEAT': '',
            'CLASS': '',
            'DESTINATION': '',
            'BAG': '',
            'BAG_PIECE': 0,
            'BAG_WEIGHT': 0,
            'BAG_ALLOWANCE': 0,
            'FF': '',
            'TKNE': '',
            'OTHER_PROPERTIES': '',
            'MSG': '',
            'ASVC': '',
            'PSPT': '',
            'EXPC': '',
            'CKIN_EXBG': '',
            'CKIN_VISA': '',
            'SEC_TXT': '',
            'OTHER_CKIN': '',
            'OTHER_MESSAGES': '',
            'BAGTAG': '',
            'VALID_TAG': '',
            'INVALID_TAG': '',
            'OPERATE': '',
            'AGENT_PID': '',
            'UNKNOWN_CONTENT': ''
        }
        # 解析PNR
        pnr_match = re.search(r'PNR\s+RL\s+([A-Z0-9]+)', record_content)
        if pnr_match:
            result['PNR'] = pnr_match.group(1)
        # 解析姓名
        name_match = re.search(r'\d\.\s([A-Z/]+)', record_content)
        # 获取姓名字符串，直到下一个换行符
        name_end_index = record_content.find('\n', name_match.end())
        name_row_remain = record_content[name_match.end():name_end_index]
        if name_match:
            result['NAME'] = name_match.group(1)
        # 解析登机号
        bn_match = re.search(r'BN\d{3}(\s{1,2}|\s\*)(\*?\w)', name_row_remain)
        if bn_match:
            result['BN'] = bn_match.group(1)
        # 解析座位
        seat_match = re.search(r'\*?(\d{1,2}[A-Z])\s+[A-Z]', name_row_remain)
        if seat_match:
            result['SEAT'] = seat_match.group(1)
        extra_seat_match = re.search(r'^\s{20,50}(\d{1,2}[A-Z])\s+ET', record_content, re.MULTILINE)
        if extra_seat_match:
            result['EXTRA_SEAT'] = extra_seat_match.group(1)
        # 解析舱位和目的地，同时捕获该行的其余部分用于OTHER_PROPERTIES
        # 解析舱位和目的地 - 合并为单个正则表达式，并捕获行的其余部分
        remainder_for_other_properties = ''
        class_dest_match = re.search(r'\s+([A-Z])\s{1}([A-Z]{3})(.*)', name_row_remain)
        if class_dest_match:
            result['CLASS'] = class_dest_match.group(1)
            result['DESTINATION'] = class_dest_match.group(2)
            # 暂存该行剩余部分，待所有已知属性解析完成后再处理OTHER_PROPERTIES
            remainder_for_other_properties = class_dest_match.group(3).strip()
        # 解析行李信息
        bag_match = re.search(r'BAG(\d+/\d+/\d+)', record_content)
        if bag_match:
            result['BAG'] = bag_match.group(1)
            bag_parts = bag_match.group(1).split('/')
            if len(bag_parts) >= 2:
                result['BAG_PIECE'] = int(bag_parts[0])
                result['BAG_WEIGHT'] = int(bag_parts[1])
        # 解析行李额度
        fba_match = re.search(r'FBA/(\d+)PC', record_content)
        if fba_match:
            result['BAG_ALLOWANCE'] = int(fba_match.group(1))
        # 解析常旅客信息
        ff_match = re.search(r'FF/([A-Z0-9/\*\s]+)', record_content)
        if ff_match:
            result['FF'] = ff_match.group(1).strip()
        # 解析票号
        tkne_match = re.search(r'TKNE/([0-9/]+)', record_content)
        if tkne_match:
            result['TKNE'] = tkne_match.group(1)
        # 注意：OTHER_PROPERTIES现在在CLASS/DESTINATION解析时处理
        # 解析MSG
        msg_match = re.search(r"MSG\s*'([^']*)'", record_content)
        if msg_match:
            result['MSG'] = msg_match.group(1)
        # 解析ASVC
        asvc_match = re.search(r'(ASVC-[^\n]+)', record_content)
        if asvc_match:
            result['ASVC'] = asvc_match.group(1)
        # 解析护照信息
        pspt_sections = []
        pspt_patterns = [
            r'PSPT-[^\n]+',
            r'PAXLST\s*:[^\n]+',
            r'PAX INFO[^\n]+',
            r'PASSPORT[^\n]+',
            r'DEST ADDR[^\n]+',
            r'ORIG ADDR[^\n]+'
        ]
        for pattern in pspt_patterns:
            matches = re.findall(pattern, record_content)
            pspt_sections.extend(matches)
        if pspt_sections:
            result['PSPT'] = '\n '.join(pspt_sections)
        # 解析EXPC
        expc_match = re.search(r'(EXPC-[^\n]+)', record_content)
        if expc_match:
            result['EXPC'] = expc_match.group(1)
        # 解析CKIN EXBG
        ckin_exbg_match = re.search(r'(CKIN EXBG[^\n]+)', record_content)
        if ckin_exbg_match:
            result['CKIN_EXBG'] = ckin_exbg_match.group(1)
        # 解析CKIN VISA
        ckin_visa_match = re.search(r'(CKIN VISA[^\n]+)', record_content)
        if ckin_visa_match:
            result['CKIN_VISA'] = ckin_visa_match.group(1)
        # 解析安全文本
        sec_txt_match = re.search(r'SEC TXT-([^\n]+)', record_content)
        if sec_txt_match:
            result['SEC_TXT'] = sec_txt_match.group(1)
        # 解析其他CKIN信息
        other_ckin = []
        ckin_patterns = [
            r'CKIN HK1[^\n]+',
            r'CKIN MTCK[^\n]+'
        ]
        for pattern in ckin_patterns:
            matches = re.findall(pattern, record_content)
            other_ckin.extend(matches)
        if other_ckin:
            result['OTHER_CKIN'] = "','".join(other_ckin)
        # 解析其他消息
        other_msg_match = re.search(r'CTC-([^A-Z]+(?:[A-Z]{3}-[^A-Z]+)*)', record_content)
        if other_msg_match:
            result['OTHER_MESSAGES'] = other_msg_match.group(1).strip()
        # 解析行李标签
        bagtag_match = re.search(r'(BAGTAG/[^\n]+)', record_content)
        if bagtag_match:
            result['BAGTAG'] = bagtag_match.group(1)
            # 解析有效和无效标签
            tags = re.findall(r'(\d{10})', bagtag_match.group(1))
            valid_tags = []
            invalid_tags = []
            for tag in tags:
                if '/PEKX' in bagtag_match.group(1) and tag in bagtag_match.group(1)[bagtag_match.group(1).find('/PEKX')-10:]:
                    invalid_tags.append(tag)
                else:
                    valid_tags.append(tag)
            result['VALID_TAG'] = ','.join(valid_tags)
            result['INVALID_TAG'] = ','.join(invalid_tags)
        # 解析操作记录
        operate_records = []
        operate_patterns = [
            r'RES AUTO[^\n]+',
            r'API [A-Z0-9\s/]+',
            r'GOV [A-Z0-9\s/]+',
            r'ACC [A-Z0-9\s/]+',
            r'BAG [A-Z0-9\s/-]+',
            r'BC\s+[A-Z0-9\s/]+',
            r'MOD [A-Z0-9\s/]+',
            r'CBT [A-Z0-9\s/-]+',
            r'BAB [A-Z0-9\s/]+'
        ]
        for pattern in operate_patterns:
            matches = re.findall(pattern, record_content)
            operate_records.extend(matches)
        if operate_records:
            result['OPERATE'] = "','".join(operate_records)
        # 解析代理PID
        agent_pids = set()
        pid_matches = re.findall(r'AGT(\d+/\d+)', record_content)
        for match in pid_matches:
            agent_pids.add(match)
        if agent_pids:
            result['AGENT_PID'] = ','.join(sorted(agent_pids))
        
        # 处理OTHER_PROPERTIES - 从剩余部分中移除已知属性
        if remainder_for_other_properties:
            # 按空格分割并过滤空字符串，获取所有项目
            other_items = [item.strip() for item in remainder_for_other_properties.split() if item.strip()]
            
            # 收集所有已解析的值，用于过滤
            known_values = set()
            # 定义所有可能的字段名
            all_fields = ['PNR', 'NAME', 'BN', 'SEAT', 'EXTRA_SEAT', 'CLASS', 'DESTINATION', 
                         'BAG', 'BAG_PIECE', 'BAG_WEIGHT', 'BAG_ALLOWANCE', 'FF', 'TKNE',
                         'MSG', 'ASVC', 'PSPT', 'EXPC', 'CKIN_EXBG', 'CKIN_VISA', 'SEC_TXT',
                         'OTHER_CKIN', 'OTHER_MESSAGES', 'BAGTAG', 'VALID_TAG', 'INVALID_TAG',
                         'OPERATE', 'AGENT_PID', 'UNKNOWN_CONTENT']
            
            for field_name in all_fields:
                if field_name in result and result[field_name] and field_name != 'OTHER_PROPERTIES':
                    field_value = result[field_name]
                    if isinstance(field_value, str):
                        # 添加完整值
                        known_values.add(field_value)
                        # 对于复合值，也添加其部分
                        if '/' in field_value:
                            known_values.update(field_value.split('/'))
                        if ',' in field_value:
                            known_values.update(field_value.split(','))
                        if "','" in field_value:
                            known_values.update(field_value.split("','"))
            
            # 过滤掉已知属性
            filtered_items = []
            for item in other_items:
                # 检查该项目是否是已知属性的一部分
                is_known = False
                for known_value in known_values:
                    if item in known_value or known_value in item:
                        is_known = True
                        break
                if not is_known:
                    filtered_items.append(item)
            
            result['OTHER_PROPERTIES'] = ','.join(filtered_items)
        else:
            result['OTHER_PROPERTIES'] = ''
        
        return result


    def query_and_parse_all_records(self) -> None:
        """查询数据库中的所有HBPR记录并解析"""
        if not os.path.exists(self.db_file):
            print(f"Database file '{self.db_file}' not found!")
            return
        print(f"Querying HBPR records from database: {self.db_file}")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # 查询所有完整记录
        cursor.execute("SELECT hbnb_number, record_content FROM hbpr_full_records ORDER BY hbnb_number")
        records = cursor.fetchall()
        conn.close()
        print(f"Found {len(records)} HBPR records to parse")
        # 解析每个记录
        for hbnb_number, record_content in records:
            print(f"Parsing HBNB {hbnb_number}...")
            parsed_result = self.parse_record(hbnb_number, record_content)
            self.parsed_results.append(parsed_result)
        print(f"Completed parsing {len(self.parsed_results)} records")


    def create_parsed_table(self) -> None:
        """创建解析结果表"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
                        CREATE TABLE IF NOT EXISTS hbpr_parsed_records (
                hbnb_number INTEGER PRIMARY KEY,
                PNR TEXT,
                NAME TEXT,
                BN TEXT,
                SEAT TEXT,
                EXTRA_SEAT TEXT,
                CLASS TEXT,
                DESTINATION TEXT,
                BAG TEXT,
                BAG_PIECE INTEGER,
                BAG_WEIGHT INTEGER,
                BAG_ALLOWANCE INTEGER,
                FF TEXT,
                TKNE TEXT,
                OTHER_PROPERTIES TEXT,
                MSG TEXT,
                ASVC TEXT,
                PSPT TEXT,
                EXPC TEXT,
                CKIN_EXBG TEXT,
                CKIN_VISA TEXT,
                SEC_TXT TEXT,
                OTHER_CKIN TEXT,
                OTHER_MESSAGES TEXT,
                BAGTAG TEXT,
                VALID_TAG TEXT,
                INVALID_TAG TEXT,
                OPERATE TEXT,
                AGENT_PID TEXT,
                UNKNOWN_CONTENT TEXT,
                parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Created hbpr_parsed_records table")


    def store_parsed_results(self) -> None:
        """存储解析结果到数据库"""
        if not self.parsed_results:
            print("No parsed results to store!")
            return
        self.create_parsed_table()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        print(f"Storing {len(self.parsed_results)} parsed results...")
        for result in self.parsed_results:
            cursor.execute('''
                INSERT OR REPLACE INTO hbpr_parsed_records 
                (hbnb_number, PNR, NAME, BN, SEAT, EXTRA_SEAT, CLASS, DESTINATION,
                 BAG, BAG_PIECE, BAG_WEIGHT, BAG_ALLOWANCE, FF, TKNE, OTHER_PROPERTIES,
                 MSG, ASVC, PSPT, EXPC, CKIN_EXBG, CKIN_VISA, SEC_TXT, OTHER_CKIN,
                 OTHER_MESSAGES, BAGTAG, VALID_TAG, INVALID_TAG, OPERATE, AGENT_PID, UNKNOWN_CONTENT)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['hbnb_number'], result['PNR'], result['NAME'], result['BN'],
                result['SEAT'], result['EXTRA_SEAT'], result['CLASS'], result['DESTINATION'],
                result['BAG'], result['BAG_PIECE'], result['BAG_WEIGHT'], result['BAG_ALLOWANCE'],
                result['FF'], result['TKNE'], result['OTHER_PROPERTIES'], result['MSG'],
                result['ASVC'], result['PSPT'], result['EXPC'], result['CKIN_EXBG'],
                result['CKIN_VISA'], result['SEC_TXT'], result['OTHER_CKIN'], result['OTHER_MESSAGES'],
                result['BAGTAG'], result['VALID_TAG'], result['INVALID_TAG'], result['OPERATE'],
                result['AGENT_PID'], result['UNKNOWN_CONTENT']
            ))
        conn.commit()
        conn.close()
        print(f"Successfully stored {len(self.parsed_results)} parsed results")


    def generate_parsing_report(self) -> None:
        """生成解析报告"""
        if not self.parsed_results:
            print("No parsing results to report!")
            return
        print("\n" + "="*60)
        print("HBPR PARSING REPORT")
        print("="*60)
        print(f"Total records parsed: {len(self.parsed_results)}")
        # 统计各字段的解析成功率
        field_stats = {}
        for result in self.parsed_results:
            for field, value in result.items():
                if field == 'hbnb_number':
                    continue
                if field not in field_stats:
                    field_stats[field] = {'total': 0, 'filled': 0}
                field_stats[field]['total'] += 1
                if value and str(value).strip():
                    field_stats[field]['filled'] += 1
        print("\nField parsing statistics:")
        for field, stats in field_stats.items():
            rate = stats['filled'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {field}: {stats['filled']}/{stats['total']} ({rate:.1f}%)")
        # 显示前几个解析结果示例
        print(f"\nFirst 3 parsing examples:")
        for i, result in enumerate(self.parsed_results[:3]):
            print(f"\n--- HBNB {result['hbnb_number']} ---")
            for field, value in result.items():
                if value and str(value).strip() and field != 'hbnb_number':
                    print(f"  {field}: {value}")
        print("="*60)


class HbprInfoProcessor:
    """HBPR信息处理器，用于处理文件和数据库操作"""


    def __init__(self, db_file: str = "CA984_25JUL25.db"):
        """
        初始化HBPR信息处理器
        Args:
            db_file: 数据库文件名
        """
        self.db_file = db_file
        self.results = []  # 存储处理结果


    def process_hbpr_file(self, hbpr_file: str) -> None:
        """
        处理HBPR文件
        Args:
            hbpr_file: HBPR文件路径
        """
        print(f"Processing HBPR file: {hbpr_file}")
        if not os.path.exists(hbpr_file):
            print(f"Error: HBPR file '{hbpr_file}' not found!")
            return
        # 读取文件内容
        with open(hbpr_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        # 分割HBPR记录
        records = self._split_hbpr_records(content)
        print(f"Found {len(records)} HBPR records")
        # 处理每个记录
        for i, record in enumerate(records):
            print(f"Processing record {i+1}/{len(records)}")
            processor = CHbpr()
            processor.run(record)
            result = {
                'hbnb_number': processor.HbnbNumber,
                'boarding_number': processor.BoardingNumber,
                'error_msg': processor.error_msg.copy(),
                'debug_msg': processor.debug_msg.copy(),
                'has_error': len(processor.error_msg) > 0,
                'original_content': record
            }
            self.results.append(result)


    def _split_hbpr_records(self, content: str) -> list:
        """
        分割HBPR记录
        Args:
            content: 文件内容
        Returns:
            记录列表
        """
        records = []
        lines = content.split('\n')
        current_record = []
        # 分割记录
        for line in lines:
            if line.strip().startswith('>HBPR:'):
                # 保存之前的记录
                if current_record:
                    records.append('\n'.join(current_record))
                # 开始新记录
                current_record = [line]
            elif line.strip().startswith('>'):
                # 其他类型的记录，结束当前HBPR记录
                if current_record:
                    records.append('\n'.join(current_record))
                    current_record = []
            else:
                # 继续当前记录
                if current_record:
                    current_record.append(line)
        # 添加最后一个记录
        if current_record:
            records.append('\n'.join(current_record))
        return records


    def store_to_database(self) -> None:
        """将处理结果存储到数据库"""
        if not self.results:
            print("No results to store!")
            return
        print(f"Storing {len(self.results)} results to database: {self.db_file}")
        # 检查数据库是否存在
        if not os.path.exists(self.db_file):
            print(f"Warning: Database '{self.db_file}' not found! Creating new tables...")
            self._create_tables()
        # 连接数据库
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # 创建处理结果表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hbpr_processing_results (
                hbnb_number INTEGER,
                boarding_number INTEGER,
                has_error BOOLEAN,
                error_count INTEGER,
                debug_count INTEGER,
                error_messages TEXT,
                debug_messages TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (hbnb_number)
            )
        ''')
        # 插入处理结果
        for result in self.results:
            cursor.execute('''
                INSERT OR REPLACE INTO hbpr_processing_results 
                (hbnb_number, boarding_number, has_error, error_count, debug_count, 
                 error_messages, debug_messages) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['hbnb_number'],
                result['boarding_number'],
                result['has_error'],
                len(result['error_msg']),
                len(result['debug_msg']),
                '\n'.join(result['error_msg']),
                '\n'.join(result['debug_msg'])
            ))
        conn.commit()
        conn.close()
        print(f"Results stored successfully!")


    def _create_tables(self) -> None:
        """创建数据库表"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        # 创建基本表结构（参考hbpr_processor.py）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flight_info (
                flight_id TEXT PRIMARY KEY,
                flight_number TEXT NOT NULL,
                flight_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hbpr_full_records (
                hbnb_number INTEGER PRIMARY KEY,
                record_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()


    def generate_report(self) -> None:
        """生成处理报告"""
        if not self.results:
            print("No results to report!")
            return
        total_records = len(self.results)
        error_records = sum(1 for r in self.results if r['has_error'])
        total_errors = sum(len(r['error_msg']) for r in self.results)
        print("\n" + "="*60)
        print("HBPR PROCESSING REPORT")
        print("="*60)
        print(f"Total records processed: {total_records}")
        print(f"Records with errors: {error_records}")
        print(f"Error rate: {error_records/total_records*100:.1f}%")
        print(f"Total error messages: {total_errors}")
        print(f"Database file: {self.db_file}")
        # 显示有错误的记录
        if error_records > 0:
            print(f"\nRecords with errors:")
            for result in self.results:
                if result['has_error']:
                    print(f"  HBNB {result['hbnb_number']} (BN {result['boarding_number']}): "
                          f"{len(result['error_msg'])} errors")
                    for error in result['error_msg'][:3]:  # 显示前3个错误
                        print(f"    - {error}")
                    if len(result['error_msg']) > 3:
                        print(f"    ... and {len(result['error_msg']) - 3} more")
        print("="*60)


def main():
    """主函数"""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--parse':
        # 解析模式：解析数据库中的HBPR记录
        print("Running in parsing mode...")
        parser = HbprRecordParser()
        parser.query_and_parse_all_records()
        parser.store_parsed_results()
        parser.generate_parsing_report()
    else:
        # 标准模式：处理HBPR文件
        hbpr_file = "sample_hbpr.txt"
        db_file = "CA984_25JUL25.db"
        # 检查输入文件
        if not os.path.exists(hbpr_file):
            print(f"Error: HBPR file '{hbpr_file}' not found!")
            return
        # 创建处理器
        processor = HbprInfoProcessor(db_file)
        # 处理文件
        processor.process_hbpr_file(hbpr_file)
        # 存储到数据库
        processor.store_to_database()
        # 生成报告
        processor.generate_report()
        print(f"\nProcessing complete! Check database '{db_file}' for results.")
        print("\nTo parse existing database records, run: python hbpr_info_processor.py --parse")


if __name__ == "__main__":
    main() 