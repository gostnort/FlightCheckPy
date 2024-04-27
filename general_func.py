
class CArgs(object):
    """This class includes the enviroment arguments for the flight"""

    #Private variables.
    __dictSub2Main = {'F':'F',
                    'A':'F',
                    'O':'F',
                    'J':'C',
                    'C':'C',
                    'D':'C',
                    'R':'C',
                    'Z':'C',
                    'I':'C'}


    def SubCls2MainCls(self,Subclass):
        result = self.__dictSub2Main.get(Subclass)
        if result == None:
            result = 'Y'
        return result
    #SubCls2MainCls() end.


    def ClassBagWeight(self,MainCls):
        dictClsWeight = {'F':32,
                       'C':32,
                       'Y':23}
        ttlWeight = dictClsWeight.get(MainCls)
        return ttlWeight
    #__ClassBagWeight() end.