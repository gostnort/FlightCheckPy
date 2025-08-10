从sample_in_25JUL.xlxs，和数据库获得数据。

在navigation中新增一个按钮。这个page能够import一个xls或xlsx文件，例如sample_in_25JUL.xlsx。结合数据库里的TKNE寻找对应的记录，在根据CKIN CCRD记录，另存一份数据表。输出的格式为'resources/Out_format.xlsx'。

输入表格和输出表格的对应如下：

输入column|输出column
:----|-----:
B|A
C|B
F|C
J|E
R|F
S|G
T|H
E|J
K|K

其他的输出表规则如下：
1. 输出表的column D总是“1”
2. 从输入表column T到输出表column H的翻译如下：

column T|column H
:------------|----------:
逾重PC|EXPC
选座|SEAT
升舱|UPG

    - 如果还有其他的类型，则照抄。

3. 输出表的column I总是”International“
4. 从数据库内查找所有包含CKIN CCRD的hbnb。命名为hbnb_list。
4. 从数据库内查找输入表column D的TKNE，如果这个记录下存在CKIN CCRD，则把这个HBNB从之前的hbnb_list中删除这个hbnb，并把CKIN CCRD信息写入输出表的同一行。CKIN CCRD 的格式解析如下：
    1. ``CKIN CCRD ITEM1 ITEM2 ITEM3``
       - ITEM1=“CASH”。那么ITEM2的内容写入输出表的column L。
       -  ITEM1=“2 letters+4 digits”。
          1. 如果前两个字母=AX，那么后面的4个digit就写入输出表的column O。Item2写入column M。
          2. 如果前两个字母是其他的内容，那么后面的4个digit就写入输出表的column O。ITEM2 写入column N。
          3. ITEM 3以及后面的内容都写入column P。
    2. 如果CKIN CCRD 不符合上面的要求，连同未被处理的hbnb_list，写入输出表SUM的C15，C16……每个CKIN CCRD的内容写一行。
       - 输出的内容要包括这个乘客姓名和TKNE内容，在加上CKIN CCRD后未能解析的内容。

正确的结果已经在sample_out_25JUL.xlsx中。