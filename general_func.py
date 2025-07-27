
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
        if result is None:
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


    def InfBagWeight(self):
        """婴儿行李重量"""
        return 23
    #InfBagWeight() end.


    def ForeignGoldFlyerBagWeight(self):
        """外籍金卡常旅客行李重量"""
        return 23
    #ForeignGoldFlyerBagWeight() end.


# Input a list with the current number list. Return a list.
# This function will get the maximum PRPD number and look for missing ones.'''
# Miss is a trouble.
def find_a_miss(source):
    # Get the maximum value in the source list
    max_value = max(source)
    
    # Create a set containing all values from 1 to max_value
    all_numbers = set(range(1, max_value + 1))
    
    # Create a set containing unique values from the source list
    unique_numbers = set(source)
    
    # Calculate the missing numbers by finding the difference between all_numbers and unique_numbers
    missing_numbers = sorted(all_numbers - unique_numbers)
    
    return missing_numbers