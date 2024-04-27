import re

def search_nacc(text):
    pd_nacc = ''
    pat=re.compile(r'PD:\s.*?,NACC')
    re_match=pat.search(text)
    index =1
    while re_match:
        re_match=pat.search(text,index)
        if re_match is None:
            break
        index=re_match.end()
        index_1st_dot=text.find('.',index)
        index_end_dot=text.rfind('.')
        pd_nacc=pd_nacc + text[index_1st_dot:index_end_dot+75]
    return pd_nacc

class pd_properties():
    __Pd_list=[]
    __Pd_item={}

    def __init__(self):
        self.__Pd_item={'name','bn','seat','cls','et'}

    def run(self,pd_text):
        index=str(pd_text).find('1.')
        if index == 0:
            return self.__Pd_list
        pd_wo_title=pd_text[index:]
        pd_list=pd_wo_title.split('.')
        for pd in pd_list:
            self.__Pd_item['name'] = self.__GetNameBnSeatCls()[0]
            self.__Pd_item['bn']=self.__GetNameBnSeatCls()[1]
            self.__Pd_item['seat']=self.__GetNameBnSeatCls()[2]
            self.__Pd_item['cls']=self.__GetNameBnSeatCls()[3]
            self.__Pd_item['et']=self.__GetEt()
            self.__Pd_item.append(self.__Pd_item)

    def __GetNameCls(self,single_pd):
        try:
            pax_name=single_pd[2:16]
            pax_name=pax_name.rstrip().lstrip()
            bn=int(single_pd[26:27])
            pax_seat=single_pd[29:33]
            pax_cls=single_pd[36]
        except:
            None
        return pax_name,bn,pax_seat,pax_cls
    
    def __GetEt(self,single_pd):
        et=''
        return et
