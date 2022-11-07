from configT import config


def generator_case():
    # Test Settings
    target_sn = "ECGRec_202142/C860265"
    target_ecgMult = [1, 2, 4]
    target_accFreq = [5, 10, 25, 50, 125, 250]
    target_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]
    target_cases = None
    # target_cases用于指定cases list，值为None时，由default_cases_generator枚举
    # 如：target_cases = [(1,5,"LiveMode","RTSMode"), (1,5,"RTSMode","LiveMode")]
    # 或：target_cases = None
    # 其中每个case的四元组参数合法值范围请参考下方的Test Constants

    ctrl_interrupt_if_log_collect_failed = False
    ctrl_skip_log_collect_if_passed = True

    # Test Constants
    allow_totalMult = 250
    allow_ecgMult = [1, 2, 4]
    allow_accFreq = [5, 10, 25, 50, 125, 250]
    allow_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]

    default_cases_generator = ((i, j, k1, k2) for i in target_ecgMult for j in target_accFreq for k1 in target_dataMode
                               for
                               k2 in target_dataMode if i * j <= allow_totalMult if
                               not ((i != 1 or j != 5) and (k1 == "DualMode" or k2 == "DualMode")) if k1 != k2 if
                               k2 != "NoneMode" if
                               not (j != 5 and (k1 == "RTSMode_SavePower" or k2 == "RTSMode_SavePower")))

    # (2, 125, 'None mode', 'Live mode')表示：这组测试是运⾏于ecg频率倍数为2,（即ecg频率为128*2=256）且acc频率基数为125 （即acc频率为125*2=250）下，将
    # Patch的数据模式从None mode切换到Live mode后进⾏的⼀组测试。

    for i in default_cases_generator:
        print(i)

    return default_cases_generator


if __name__ == '__main__':
    generator_case()
    print(config.dev_log_root)
    allow_dataSwitch_T = config.allow_dataSwitch_T
    print(type(allow_dataSwitch_T))
    for i in allow_dataSwitch_T.values():
        print(i)
