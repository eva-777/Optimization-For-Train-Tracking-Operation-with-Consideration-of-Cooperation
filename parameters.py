import numpy as np
import pandas as pd
import math


######################################## 列车与线路参数 ########################################

""" 列车参数定义 """
TRAIN_LEN = 120 # m 
MAX_VELO = 80 / 3.6  # 最大速度 500 km/h，转换为 138.89 m/s
MAX_ACC = 1  # 最大加速度 1 m/s^2
MIN_ACC = -1  # 最大减加速度 1 m/s^2
MAX_Delta_ACC = 0.5  # 加速度最大变化值 0.5 m/s^3  # atten 加速度变化率是在时域上探讨，而现有模型是空间域模型，难以计算加速度变化率
NUM = 6  # 列车编组数6：3动3拖
MASS = 284.055*1000  # 列车总质量，单位 kg， [B型车：空载194.295t，定员284.055t，超员307.095t]

MA_CBTC = 2.4 # CBTC中MA的计算耗时，单位 s
MA_TACS = 0.36 # TACS中MA的计算耗时，单位 s

RE_DS = 200  # 再生制动的基准距离
RE_EFF = 0.9  # 再生制动过程中，动能转换为电能的效率

""" 线路参数定义 """
# 加载文件
line_file = 'D:/Python/Jupyter_Code/CASCO/paper1/Songjiazhuang_railline.xlsx'
line_df = pd.read_excel(line_file)
column_name1 = ['order', 'distance', 'operation_time', 'dwell_time', 'a_distance', 'a_operation_time',
               'sl_starting', 'sl_end', 'speed_limit', 'g_starting', 'g_end', 'gradient']
column_data1 = line_df[column_name1]

station_values = ['distance', 'operation_time', 'dwell_time', 'a_distance', 'a_operation_time']
station_keys = line_df['order']
station_info = {}
for key in station_keys:
    sub_df = line_df[station_keys == key]  # 获取每个键对应的行 --> DataFrame
    if not sub_df.empty:  # 确保每个键只有一个记录
        station_info[key] = sub_df[station_values].iloc[0].to_dict()  # 将值列转换为字典并添加到有序字典中  --> dict

station_a_distance = column_data1['a_distance'].dropna().to_list()
station_a_distance.insert(0, 0)

# 线路限速
speed_limit = column_data1['speed_limit'].dropna().to_list()  # num idx = 34
speed_limit = [limit/3.6 for limit in speed_limit]
speed_limit_switch = column_data1['sl_starting'].dropna().to_list() # 35
# 线路坡度
gradient = column_data1['gradient'].dropna().astype(float).to_list()   # num idx = 56
gradient_switch = column_data1['g_starting'].dropna().to_list()   # num idx = 57

# 划分section
section = gradient_switch + speed_limit_switch + station_a_distance  # m, num = 102
section = list(set(section))
section.sort()
section_len = []  # m, num = 101
for i in range(len(section)-1):
    section_len.append(round((section[i+1]-section[i]),2))  # min = 9, max = 700

# 线路曲率
curvature = []  # 暂无

# 划分subsection
DS = 5
sub_num = []  # 区间个数 len(sub_num) = 101; 子区间个数 num = 2307, when DS=10; num = 4579, when DS=5
sub_len = []  # 线路总长 sum(sub_len) = 22728;
for i in range(len(section_len)):
    sub_num.append(math.ceil(section_len[i] / DS))
    temp_1 = [DS] * int(section_len[i] / DS)  # mid_xx 中间变量
    if (section_len[i] % DS) != 0:
        temp_1.append(section_len[i] % DS)
    sub_len += temp_1

""" 构建线路位置(distance of subsection)和线路限速、坡度的映射 """
# 构建sub_dist
sub_dist = [0]  # sub_dist个数 num = 2308, when DS=10; num = 4580, when DS=5
temp_2 = 0
for i in range(len(sub_len)):
    temp_2 += sub_len[i]
    sub_dist.append(temp_2)

# 构建speed_map
speed_map = {}  # 创建字典
for i in range(len(speed_limit)):  # 遍历速度限制和速度限制切换点，构建映射关系
    start_1 = speed_limit_switch[i]  # 获取当前区间的起点和终点
    end_1 = speed_limit_switch[i + 1]
    speed_map[(start_1, end_1)] = speed_limit[i]  # 将区间和对应的速度限制添加到字典中

# 使用speed_map将distance中的每个位置映射到speed_limit
sub_spdlim = []
for dist in sub_dist:  # 取出位置
    for interval, limit in speed_map.items():  # 遍历每个速度区间
        if interval[0] <= dist <= interval[1]:
            sub_spdlim.append(limit)
            break
sub_spdlim.pop(0)

# 线路限速与位置组合成字典
sub_spdlim_dict = {dist: (len, spdlim) for dist, len, spdlim in zip(sub_dist[1:], sub_len, sub_spdlim)}

# 构建gradient_map
gradient_map = {}  # 创建字典
for i in range(len(gradient)):  # 遍历速度限制和速度限制切换点，构建映射关系
    start_1 = gradient_switch[i]  # 获取当前区间的起点和终点
    end_1 = gradient_switch[i + 1]
    gradient_map[(start_1, end_1)] = gradient[i]  # 将区间和对应的速度限制添加到字典中


# 使用gradient_map将distance中的每个位置映射到gradient
sub_gradient = []
for dist in sub_dist:  # 取出位置
    for interval, limit in gradient_map.items():  # 遍历每个速度区间
        if interval[0] <= dist <= interval[1]:
            sub_gradient.append(limit)
            break
sub_gradient.pop(0)


""" 车站索引 """
sub_dist = np.array(sub_dist)
station_idx = [np.where(sub_dist==each_distance)[0].tolist()[0] for each_distance in station_a_distance]

""" 运行参数定义 """
OP_TIME_ALL = 2077  # 运行时限，单位：s ; 最短运行时间为 552.8 s
op_time = column_data1['operation_time'].dropna().to_list()
dw_time = column_data1['dwell_time'].dropna().to_list()


######################################## 牵引力、基本阻力、附加阻力 ########################################

"""  牵引力、基本阻力、重力分力  """
def f_t(v):  # 牵引力
    """
    parameters: v -- velocity (m/s)
    return: f_t -- max traction force (N)
    """
    f_t = 0
    if 0 <= v <= 36/3.6:
        f_t = 312.87
    elif 36/3.6 < v <= 48/3.6:
        # f_t = -7.10157*(v*3.6) + 568.5264
        f_t = -25.56564*v + 568.5264
    elif v > 48/3.6:
        # f_t = 0.0978*(v*3.6)**2 - 16.86*(v*3.6) + 811.6
        f_t = 1.267488*v**2 - 60.696*v +811.6
        
    return f_t * 1000

def f_b(v):  # 制动力 <= 宿帅论文，自己计算
    """
    parameters: v -- velocity (m/s)
    return: f_b -- min braking force (N)
    """
    f_b = 0

    if 0 <= v <= 60/3.6:
        f_b = 258.4
    elif v > 60/3.6:
        f_b = -18.612*v + 568.6

    return f_b * 1000

def f_b_r(v):  # 基本阻力：空气阻力、车轮滚动阻力、轮轨间滑动阻力、振动阻力、轴承摩擦阻力 => 戴维斯方程
    """
    parameter: v -- velocity (km/h)
    return: f_r -- basic running resistance (N)
    """
    f_b_r = 0
    f_b_r = 0.001293*(v*3.6)**2 + 0.014*(v*3.6) + 2.4

    return f_b_r*1000

# def f_addition_r(MASS, gradient, curvature, tlength): # 附加阻力：坡度、曲线、隧道
def f_a_r(gradient): # 附加阻力：坡度、曲线、隧道
    """
    parameter: gradient -- 坡度 (千分数), curvature -- 曲线半径(m), tlength -- 隧道长度(m)
    return: f_a_r -- additional running resistance (N)
    """
    g = 9.8015  # 北京重力加速度 N/kg
    w_g = gradient/1000
    # w_c = 600/curvature
    # w_t = 0.00013*tlength
    f_a_r = MASS * g *(w_g)

    return f_a_r



######################################## 列车类定义 ########################################

""" 定义列车类 """
class Train:
    def __init__(self):
        self.idx = []
        self.state = []
        self.t = []
        self.s = []
        self.v = []
        self.a = []
        self.f_t = []
        self.f_b = []
        self.e = []
        self.ree = []
        self.arrival_time = []

    def clear(self):  # 清除所有列表中的数据
        self.idx.clear()
        self.state.clear()
        self.t.clear()
        self.s.clear()
        self.v.clear()
        self.a.clear()
        self.f_t.clear()
        self.f_b.clear()
        self.e.clear()
        self.ree.clear()
        self.arrival_time.clear()
    
    def listExpand(self, value):  # 扩展list
        self.idx.append(value)
        self.state.append(value)
        self.t.append(value)
        self.s.append(value)
        self.v.append(value)
        self.a.append(value)
        self.f_t.append(value)
        self.f_b.append(value)
        self.e.append(value)
        self.ree.append(value)

