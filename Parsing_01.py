# Parsing_01.py

import struct
import pandas as pd
from datetime import datetime
import os
import pandas as pd
import numpy as np
import csv
import sqlite3
from tqdm import tqdm

class File_search:
    def __init__(self, root_path):
        self.folder_path = root_path
        self.file_extensions = ('.cyc', '.cts', '.sch')
        
    def find_files(self):
        result = {ext: [] for ext in self.file_extensions}
        file_name = []
        for dirpath, dirnames, filenames in os.walk(self.folder_path):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in result:
                    result[ext].append(os.path.join(dirpath, filename))
        return result['.cyc'], result['.cts'], result['.sch']
    
    def integration_list(self, pair=True):
        cyc_list, cts_list, sch_list = self.find_files()
        result = {'.cyc': [], '.cts': [], '.sch': []}
        paired_result = []

        for temp_cyc in cyc_list:
            temp_cts = temp_cyc.replace('.cyc', '.cts')
            if temp_cts in cts_list:
                temp_sch = temp_cts.replace('.cts', '.sch')
                if temp_sch in sch_list:
                    result['.cyc'].append(temp_cyc)
                    result['.cts'].append(temp_cts)
                    result['.sch'].append(temp_sch)

        if pair == False:
            return result
        else:
            for cyc_idx, cts_idx, sch_idx in zip(result['.cyc'], result['.cts'], result['.sch']):
                paired_result.append({
                    '.cyc': cyc_idx,
                    '.cts': cts_idx,
                    '.sch': sch_idx
                })
            return paired_result
        

# =============================================================================
# RECORD_ITEM_MAP (.cts / .cyc 공통)
# =============================================================================
# =============================================================================
# RECORD_ITEM_MAP
# .cts 파일 스펙 문서에 정의된 wRecordItem ID → (컬럼명, 데이터타입) 매핑 테이블
# key   : wRecordItem ID (16진수)
# value : (컬럼명, struct 포맷 문자)
#         "f" = 4bytes float (IEEE 754 single precision)
#         "I" = 4bytes unsigned int (ULONG)
# =============================================================================

class Version:
    def __init__(self, version):
        self.version = version
        self.version_list = [16386, 12291, 8196, 4103, 16385, 12290, 8195, 4102,
            12289, 8194, 4101, '4101_GAS', 8193, 4100, 4099, 4097, 4096]

    def check_version(self):
        if self.version in self.version_list:
            print(f".cyc, .cts Version {self.version} check OK")
            return self.version
        else:
            print(f"WARNING: unknown version {self.version}")
            return None

    def record_item_map(self):
        version = self.check_version()
        common_record_item_map = {0x00:("PS_STATE","I"), 0x01:("PS_VOLTAGE","f"), 0x02:("PS_CURRENT","f"), 0x03:("PS_CAPACITY","f"), 0x04:("PS_IMPEDANCE","f"), 0x05:("PS_CODE","I"), 0x06:("PS_STEP_TIME","f"), 0x07:("PS_TOT_TIME","f"), 0x08:("PS_GRADE_CODE","I"), 0x09:("PS_STEP_NO","I"),
                                  0x0A:("PS_WATT","f"), 0x0B:("PS_WATT_HOUR","f"), 0x0C:("PS_TEMPERATURE","f"), 0x0D:("PS_PRESSURE","f"), 0x0E:("PS_STEP_TYPE","I"),0x0F:("PS_CUR_CYCLE","I"), 0x10:("PS_TOT_CYCLE","I"), 0x11:("PS_TEST_NAME","f"), 0x12:("PS_SCHEDULE_NAME","f"), 0x13:("PS_CHANNEL_NO","I"),
                                  0x14:("PS_MODULE_NO","I"), 0x15:("PS_LOT_NO","f"), 0x16:("PS_DATA_SEQ","f"), 0x17:("PS_AVG_CURRENT","f"), 0x18:("PS_AVG_VOLTAGE","f"),0x19:("PS_CAPACITY_SUM","f"), 0x1A:("PS_CHARGE_CAP","f"), 0x1B:("PS_DISCHARGE_CAP","f"), 0x1C:("PS_METER_DATA","f"), 0x1D:("PS_START_TIME","f"),
                                  0x1E:("PS_END_TIME","f"), 0x1F:("PS_SHARING_INFO","f"), 0x20:("PS_GOTO_COUNT","I"), 0x21:("PS_WATTHOUR_SUM","f"), 0x22:("PS_CHAR_WATTHOUR","f"),0x23:("PS_DISCHAR_WATTHOUR","f"), 0x24:("PS_INTEGRAL_CAPACITY","f"), 0x25:("PS_INTEGRAL_WATTHOUR","f"), 0x26:("PS_CV_END_TIME","f"), 0x27:("PS_CYCLE_NUM","f"),
                                  0x28:("PS_TOT_TIME_CARRY","I"), 0x29:("PS_FARAD","f"), 0x2A:("PS_TEMPERATURE2","f"), 0x2B:("PS_DQDV","f"), 0x2C:("PS_CHARGE_CC_CAP","f"),0x2D:("PS_CHARGE_CV_CAP","f"), 0x2E:("PS_DISCHARGE_CC_CAP","f"), 0x2F:("PS_DISCHARGE_CV_CAP","f"), 0x30:("PS_REALDATE","f"), 0x31:("PS_REALCLOCK","f"),
                                  0x32:("PS_CHAMBER_TEMPERATURE","f"), 0x33:("PS_AUX_TEMPERATURE","f"), 0x34:("PS_AUX_VOLTAGE","f"), 0x3B:("PS_AUX_THICKNESS2","f"),0x3C:("PS_AUX_PRESSURE1","f"), 0x3D:("PS_AUX_PRESSURE2","f"), 0x3E:("PS_AUX_PRESSURE3","f"), 0x3F:("PS_AUX_PRESSURE4","f"),
                                  0x40:("PS_AUX_THICKNESS1","f"), 0x49:("PS_AMBIENT_TEMP","f"), 0x4A:("PS_GAS_VOLTAGE","f"), 0x4B:("PS_IMPEDANCE_100MS","f"),0x4C:("PS_IMPEDANCE_1S","f"), 0x4D:("PS_IMPEDANCE_5S","f"), 0x4E:("PS_IMPEDANCE_30S","f"), 0x4F:("PS_IMPEDANCE_60S","f")}
        common_state = {0x0000:"PS_STATE_IDLE",0x0001:"PS_STATE_STANDBY",0x0002:"PS_STATE_RUN",0x0003:"PS_STATE_PAUSE",0x0004:"PS_STATE_MAINTENANCE"}
        common_steptype = {0x00:"PS_STEP_NONE",0x01:"PS_STEP_CHARGE",0x02:"PS_STEP_DISCHARGE",0x03:"PS_STEP_REST",0x04:"PS_STEP_OCV",0x05:"PS_STEP_IMPEDANCE",0x06:"PS_STEP_END",0x07:"PS_STEP_ADV_CYCLE",0x08:"PS_STEP_LOOP",0x09:"PS_STEP_PATTERN",0x0A:"PS_STEP_BALANCE",0x0B:"PS_STEP_USERMAP"}
        common_dataselect = {0x00:"SFT_SAVE_REPORT", 0x01:"SFT_SAVE_STEP_END", 0x02:"SFT_SAVE_DELTA_TIME", 0x03:"SFT_SAVE_DELTA_V", 0x04:"SFT_SAVE_DELTA_I", 0x05:"SFT_SAVE_DELTA_T", 0x06:"SFT_SAVE_DELTA_P", 0x07:"SFT_SAVE_ETC"}
        common_mode = {0x01:"PS_MODE_CCCV",0x02:"PS_MODE_CC",0x03:"PS_MODE_CV",0x04:"PS_MODE_DCIMP",0x05:"PS_MODE_ACIMP",0x06:"PS_MODE_CP",0x07:"PS_MODE_PUSE",0x08:"PS_MODE_CR"}
        common_step_state = {0: "Normal", 1: "NonCell", 2: "System Error", 3: "Defective Cell", 4: "Cell Check Error",64: "Time Complete", 65: "Voltage Complete", 66: "Current Complete", 67: "Capacity Complete", 68: "OCV Step Complete",
                        69: "Last Step Complete", 70: "Stopped by User", 71: "Pause", 72: "Check Step Complete", 73: "Ended for Next Step", 74: "Impedance Step Completed", 75: "ADV Step Completed", 76: "LOOP Step Completed", 77: "Delta Voltage Completed", 78: "SOC Completed",
                        79: "Temperature Completed", 80: "Process completed(Time)", 81: "Process completed(Voltage)", 82: "Process completed(Current)",83: "Process completed(Capacity)", 84: "Process completed(Watt)", 85: "Process completed(WattHour)", 86: "Standby(Temper.)", 87: "Short Test Completed", 90: "Watt Complete", 91: "WattHour Complete", 92: "Accumulated Capacity Complete", 93: "Accumulated WattHour Complete", 94: "Cycle Time Complete",
                        95: "CV Time Complete", 96: "Inspection Overvoltage", 97: "Inspection Undervoltage", 98: "Inspection Upper Limit Voltage", 99: "Inspection Lower Limit Voltage",100: "Inspection Upper Limit Current", 101: "Inspection Lower Limit Current", 102: "Contact Failure 1", 103: "Contact Failure 2", 104: "Contact Failure 3",105: "BadCell1", 106: "BadCell2", 107: "BadCell3", 108: "Short", 109: "Location Error (None)",
                        110: "Location Error ()", 111: "Drop Voltage Error", 128: "Voltage Upper Limit", 129: "Voltage Lower Limit", 130: "LimitI Pause",131: "LimitI End", 134: "OCV Upper Limit", 135: "OCV Lower Limit", 136: "Current Upper Limit", 137: "Current Lower Limit",138: "LimitV Pause", 139: "LimitV End", 142: "Capacity Upper Limit", 143: "Capacity Lower Limit", 152: "User Completion",153: "Pause Completion", 154: "Next Step Completion", 165: "Temperature Upper Limit", 166: "Temperature Lower Limit", 167: "Pattern Info. Read Error",
                        168: "JIG Sensor Error", 169: "Chamber Error", 170: "Inverter Error", 171: "Equipment Stop", 172: "=+Compare Line Error", 173: "-Compare Line Error",174: "Compare Line Ch. Error", 175: "Voltage Compare Upper Limit", 176: "Current Compare Upper Limit", 177: "Temper. Compare Excess", 178: "Meter Compare Upper Limit",179: "Meter Compare Lower Limit", 180: "JIG Error", 181: "Cut of Temper. Line Wire", 182: "Network Connection Error", 183: "Short Tester Error",184: "Short Tester Connection Error", 186: "Short Tester Singleness Mode", 208: "Voltage Error (Warning)",
                        209: "Current Error (Warning)", 210: "Circuit Overheat (Warning)", 211: "Control Power Error (SMPS)", 212: "Power Off(Switch)",
                        213: "UPS Power Error", 214: "UPS Battery Error", 215: "EMG (MAIN)", 216: "EMG (SUB)", 217: "Network Error", 220: "AUX Temper. Completed",
                        221: "AUX Temper. Upper Limit Complet", 222: "AUX Temper. Lower Limit Complet", 223: "AUX Volt. Completed", 224: "AUX Volt. Upper Limit Completed",
                        225: "AUX Volt. Lower Limit Completed", 226: "AUX Temper. Upper Limit", 227: "AUX Temper. Lower Limit", 228: "AUX Volt. Upper Limit",
                        229: "AUX Volt. Lower Limit", 230: "Temper. Excess Completed", 231: "DC Fan Error", 232: "Capa. Efficiency Complete", 233: "Capa. Efficiency Pause", 234: "Capa. Efficiency Cycle Complete", 235: "Cycle Capacity Complete", 236: "Power Efficiency Cycle Complete", 237: "Imp. Efficiency Cycle Complete", 238: "Power Efficiency Pause", 239: "Imp. Efficiency Pause", 240: "Cycle Voltage Complete", 241: "Cycle Voltage End", 242: "Door Open Detected", 243: "Smoke Detected", 244: "Delta Voltage Error", 245: "Delta Current Error", 246: "Delta Voltage Complete", 247: "Delta Current Complete", 248: "Capa. Efficiency Complete", 249: "Power Efficiency Complete", 250: "Imp. Efficiency Complete", 251: "Pause(Grade Check)", 252: "Complete(Grade Check)", 253: "Channel Error in Same Chamber", 260: "[PCU]Input Voltage Error", 261: "[PCU]Voltage Upper Limit", 262: "[PCU]Current Upper Limit", 263: "[PCU]Temperature Upper Limit", 264: "[PCU]PV Voltage Error", 265: "[PCU]Terminal Voltage Error",
                        266: "[PCU]Output Current Error", 268: "[PCU]Dischar. Vol. Source Error", 269: "[PCU]Output Curr. Balance Error", 270: "[PCU]External Relay Error", 271: "[PCU]output Contact Error", 273: "[PCU]Communication Error", 274: "[PCU]Unknown Error", 275: "[PCU]Work Mode Error", 276: "[PCU]LAN Connect Error", 277: "[PCU]Sequence No. Error", 280: "[INV]LAG SHORT CURR.", 281: "[INV]OVER CURRENT", 282: "[INV]OVER VOLTAGE", 283: "[INV]PRECHARGE FAIL", 284: "[INV]OVER CURRENT 2", 285: "[INV]CAN ERROR", 286: "[INV]OVER LOAD", 287: "[INV]OVER HEAT", 289: "[INV]LOW VOLTAGE", 291: "[INV]RESET 1", 292: "[INV]RESET 2", 293: "[INV]AC INPUT FAIL", 295: "[INV]HDC ERROR", 296: "[INV]STAND-BY", 310: "CV Fault Voltage Error",
                        311: "CV Fault Current Error", 315: "Diagnosis Pause", 316: "Diagnosis Complete", 318: "3rd Current Calculation Anomaly", 360: "TVOC Upper",361: "TVOC Lower", 362: "eCO2 Upper", 363: "eCO2 Lower", 364: "TVOC Complete", 365: "eCO2 Complete", 400: "Sample Vent Detect",401: "Sample Vent Detect", 402: "Rest Voltage Error", 403: "Chamber SV Error", 404: "Temp upper(EMG)", 405: "Sample Soft Vent Detect",406: "Sample Hard Vent Detect", 412: "Voltage upper(MonPro)", 413: "Voltage upper(OVP)", 416: "Temp upper(MonPro)", 417: "Temp upper(OTP)", 418: "Voltage lower(MonPro)", 419: "Pause by group(OVP)", 420: "Pause by group(OTP)", 421: "Chamber DI Error", 422: "Chamber SV, Ambient Temp Deviation Error", 
                        423: "Group Voltage Error", 424: "Group Time Error", 426: "Chamber Stop", 500: "COMServer Communication Error", 1128: "Voltage upper(Step)", 1129: "Voltage lower(Step)", 1134: "Voltage upper(Step)", 1135: "Voltage lower(Step)", 1136: "Current upper(Step)", 1137: "Current lower(Step)", 1142: "Capacity upper(Step)", 1143: "Capacity lower(Step)", 1165: "Temp upper(Step)", 1166: "Temp lower(Step)", 2134: "Voltage upper(Test)", 2135: "Voltage lower(Test)", 2128: "Voltage upper(Test)", 2129: "Voltage lower(Test)", 2136: "Current upper(Test)", 2137: "Current lower(Test)",
                        2142: "Capacity upper(Test)", 2143: "Capacity lower(Test)", 2165: "Temp upper(Test)", 2166: "Temp lower(Test)"}
        record_map = common_record_item_map.copy()
        state_map = common_state.copy()
        steptype_map = common_steptype.copy()
        dataselect_map = common_dataselect.copy()
        mode_map = common_mode.copy()
        step_state_map = common_step_state.copy()
        add_item_map = {}
        add_steptype = {}
        add_mode = {}
        
        if version == 16386:
            add_item_map = {0x50:("PS_EIS_FREQUNECY","f"), 0x51:("PS_EIS_I_REAL","f"), 0x52:("PS_EIS_I_IMAGINARY","f"), 0x53:("PS_EIS_TEMPERATURE1","f"), 0x54:("PS_EIS_TEMPERATURE2","f"),0x55:("PS_EIS_TEMPERATURE3","f"), 0x56:("PS_EIS_PRESSURE1","f"), 0x57:("PS_EIS_PRESSURE2","f"), 0x58:("PS_EIS_PRESSURE3","f"), 0x59:("PS_EIS_PRESSURE4","f"),
                            0x5A:("PS_EIS_PRESSURE5","f"), 0x5B:("PS_EIS_PRESSURE6","f"), 0x5C:("PS_EIS_PRESSURE7","f"), 0x5D:("PS_EIS_PRESSURE8","f"), 0x5E:("PS_AUX_TEMPERATURE1","f"),0x5F:("PS_AUX_TEMPERATURE2","f"), 0x60:("PS_AUX_TEMPERATURE3","f"), 0x61:("PS_AUX_TEMPERATURE4","f"), 0x62:("PS_AUX_TEMPERATURE5","f"), 0x63:("PS_AUX_VOLTAGE1","f"),
                            0x64:("PS_AUX_VOLTAGE2","f"), 0x65:("PS_AUX_VOLTAGE3","f"), 0x66:("PS_AUX_VOLTAGE4","f"), 0x67:("PS_AUX_VOLTAGE5","f"), 0x68:("PS_CHAMBER_TEMP_SV","f"),0x69:("PS_CHILER_TEMP_PV","f"), 0x6A:("PS_CHILER_TEMP_SV","f"), 0x6B:("PS_CHILER_PUMP_PV","f"), 0x6C:("PS_CHILER_PUMP_SV","f"), 0x6D:("PS_AUX_THICKNESS3","f"),
                            0x6E:("PS_AUX_THICKNESS4","f"), 0x70:("PS_RESTORED_FLAG","f"), 0x71:("PS_CALI_MODE_STATE","I")}
        elif version == 12291:
            add_item_map = {0x50:("PS_EIS_FREQUNECY","f"), 0x51:("PS_EIS_I_REAL","f"), 0x52:("PS_EIS_I_IMAGINARY","f"), 0x53:("PS_EIS_TEMPERATURE1","f"), 0x54:("PS_EIS_TEMPERATURE2","f"),0x55:("PS_EIS_TEMPERATURE3","f"), 0x56:("PS_EIS_PRESSURE1","f"), 0x57:("PS_EIS_PRESSURE2","f"), 0x58:("PS_EIS_PRESSURE3","f"), 0x59:("PS_EIS_PRESSURE4","f"),
                            0x5A:("PS_EIS_PRESSURE5","f"), 0x5B:("PS_EIS_PRESSURE6","f"), 0x5C:("PS_EIS_PRESSURE7","f"), 0x5D:("PS_EIS_PRESSURE8","f"), 0x5E:("PS_AUX_TEMPERATURE1","f"),0x5F:("PS_AUX_TEMPERATURE2","f"), 0x60:("PS_AUX_TEMPERATURE3","f"), 0x61:("PS_AUX_TEMPERATURE4","f"), 0x62:("PS_AUX_TEMPERATURE5","f"), 0x63:("PS_AUX_VOLTAGE1","f"),
                            0x64:("PS_AUX_VOLTAGE2","f"), 0x65:("PS_AUX_VOLTAGE3","f"), 0x66:("PS_AUX_VOLTAGE4","f"), 0x67:("PS_AUX_VOLTAGE5","f"), 0x68:("PS_CHAMBER_TEMP_SV","f"),0x69:("PS_CHILER_TEMP_PV","f"), 0x6A:("PS_CHILER_TEMP_SV","f"), 0x6B:("PS_CHILER_PUMP_PV","f"), 0x6C:("PS_CHILER_PUMP_SV","f"), 0x6D:("PS_AUX_THICKNESS3","f"),
                            0x6E:("PS_AUX_THICKNESS4","f"), 0x70:("PS_RESTORED_FLAG","f"), 0x71:("PS_CALI_MODE_STATE","I")}
            add_steptype = {0x0F : "PS_STEP_EIS"}
        elif version == 8196:
            add_item_map = {0x68:("PS_CHAMBER_TEMP_SV","f"), 0x69:("PS_CHILER_TEMP_PV","f"), 0x6A:("PS_CHILER_TEMP_SV","f"), 0x6B:("PS_CHILER_PUMP_PV","f"),0x6C:("PS_CHILER_PUMP_SV","f"), 0x6D:("PS_AUX_THICKNESS3","f"), 0x6E:("PS_AUX_THICKNESS4","f"), 0x70:("PS_RESTORED_FLAG","f"),
                            0x71:("PS_CALI_MODE_STATE","I")}    
        elif version == 4103:
            add_item_map = {0x68:("PS_CHAMBER_TEMP_SV","f"), 0x69:("PS_CHILER_TEMP_PV","f"), 0x6A:("PS_CHILER_TEMP_SV","f"), 0x6B:("PS_CHILER_PUMP_PV","f"),0x6C:("PS_CHILER_PUMP_SV","f"), 0x6D:("PS_AUX_THICKNESS3","f"), 0x6E:("PS_AUX_THICKNESS4","f"), 0x70:("PS_RESTORED_FLAG","f"),
                            0x71:("PS_CALI_MODE_STATE","I")}
        elif version == 16385:
            add_item_map = {0x50:("PS_EIS_FREQUNECY","f"), 0x51:("PS_EIS_I_REAL","f"), 0x52:("PS_EIS_I_IMAGINARY","f"), 0x53:("PS_EIS_TEMPERATURE1","f"),0x54:("PS_EIS_TEMPERATURE2","f"), 0x55:("PS_EIS_TEMPERATURE3","f"), 0x56:("PS_EIS_PRESSURE1","f"), 0x57:("PS_EIS_PRESSURE2","f"),
                            0x58:("PS_EIS_PRESSURE3","f"), 0x59:("PS_EIS_PRESSURE4","f"), 0x5A:("PS_EIS_PRESSURE5","f"), 0x5B:("PS_EIS_PRESSURE6","f"),0x5C:("PS_EIS_PRESSURE7","f"), 0x5D:("PS_EIS_PRESSURE8","f"), 0x5E:("PS_AUX_TEMPERATURE1","f"), 0x5F:("PS_AUX_TEMPERATURE2","f"),
                            0x60:("PS_AUX_TEMPERATURE3","f"), 0x61:("PS_AUX_TEMPERATURE4","f"), 0x62:("PS_AUX_TEMPERATURE5","f"), 0x63:("PS_AUX_VOLTAGE1","f"),0x64:("PS_AUX_VOLTAGE2","f"), 0x65:("PS_AUX_VOLTAGE3","f"), 0x66:("PS_AUX_VOLTAGE4","f"), 0x67:("PS_AUX_VOLTAGE5","f"), 0x70:("PS_RESTORED_FLAG","f")}
            add_mode = {0x08:"PS_MODE_CR"}
        elif version == 12290:
            add_item_map = {0x50:("PS_EIS_FREQUNECY","f"), 0x51:("PS_EIS_I_REAL","f"), 0x52:("PS_EIS_I_IMAGINARY","f"), 0x53:("PS_EIS_TEMPERATURE1","f"),0x54:("PS_EIS_TEMPERATURE2","f"), 0x55:("PS_EIS_TEMPERATURE3","f"), 0x56:("PS_EIS_PRESSURE1","f"), 0x57:("PS_EIS_PRESSURE2","f"),
                            0x58:("PS_EIS_PRESSURE3","f"), 0x59:("PS_EIS_PRESSURE4","f"), 0x5A:("PS_EIS_PRESSURE5","f"), 0x5B:("PS_EIS_PRESSURE6","f"),0x5C:("PS_EIS_PRESSURE7","f"), 0x5D:("PS_EIS_PRESSURE8","f"), 0x70:("PS_RESTORED_FLAG","f")}
            add_steptype = {0x0F : "PS_STEP_EIS"}
            add_mode = {0x08:"PS_MODE_CR"}
        elif version == 8195:
            add_item_map = {0x70:("PS_RESTORED_FLAG","f")}
            add_mode = {0x08:"PS_MODE_CR"}
        elif version == 4102:
            add_item_map = {0x70:("PS_RESTORED_FLAG","f")}
            add_mode = {0x08:"PS_MODE_CR"}
        elif version == 12289:
            add_item_map = {0x50:("PS_EIS_FREQUNECY","f"), 0x51:("PS_EIS_I_REAL","f"), 0x52:("PS_EIS_I_IMAGINARY","f"), 0x53:("PS_EIS_TEMPERATURE1","f"),0x54:("PS_EIS_TEMPERATURE2","f"), 0x55:("PS_EIS_TEMPERATURE3","f"), 0x56:("PS_EIS_PRESSURE1","f"), 0x57:("PS_EIS_PRESSURE2","f"),
                            0x58:("PS_EIS_PRESSURE3","f"), 0x59:("PS_EIS_PRESSURE4","f"), 0x5A:("PS_EIS_PRESSURE5","f"), 0x5B:("PS_EIS_PRESSURE6","f"), 0x5C:("PS_EIS_PRESSURE7","f"), 0x5D:("PS_EIS_PRESSURE8","f")}    
            add_steptype = {0x0F : "PS_STEP_EIS"}
            add_mode = {0x08:"PS_MODE_CR"}
        elif (version == 8194) or (version == 4101):
            add_mode = {0x08:"PS_MODE_CR"}
        elif version == '4101_GAS':
            add_item_map = {0x41:("PS_GAS_CO2","f"), 0x42:("PS_GAS_TEMP","f"), 0x43:("PS_GAS_AH","f"), 0x44:("PS_GAS_BASELINE","f"),0x45:("PS_GAS_TVOC","f"), 0x46:("PS_GAS_ETHANOL","f"), 0x47:("PS_GAS_H2","f")}
            del_item = [0x49,0x4A,0x4B,0x4C,0x4D,0x4E,0x4F,0x3B,0x3C,0x3D,0x3E,0x3F,0x40]
            record_map = {k: v for k, v in record_map.items() if k not in del_item}
            add_mode = {0x08:"PS_MODE_CR"}
        elif (version == 8193) | (version == 4100):
            del_item = [0x49,0x4A,0x4B,0x4C,0x4D,0x4E,0x4F,0x3B,0x3C,0x3D,0x3E,0x3F,0x40]
            record_map = {k: v for k, v in record_map.items() if k not in del_item}
        # elif version == 4099:
        #     del_item = [0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40]
        #     record_map = {k: v for k, v in record_map.items() if k not in del_item}
        # elif version == 4097:
        #     del_item = [0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40]
        #     record_map = {k: v for k, v in record_map.items() if k not in del_item}
        # elif version == 4096:
        #     del_item = [0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,0x30, 0x31, 0x32, 0x33, 0x34,0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40]
        #     record_map = {k: v for k, v in record_map.items() if k not in del_item}
        record_map.update(add_item_map)
        steptype_map.update(add_steptype)
        mode_map.update(add_mode)
        
        # print(f"Record item of {self.version} : {len(record_map)}")
        # print(f"Record item of {self.version} : {len(steptype_map)}")
        # print(f"Record item of {self.version} : {len(mode_map)}")
        return record_map, state_map, dataselect_map, steptype_map, mode_map, step_state_map
    
class CycParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def _read_str(self, f, size):
        raw = f.read(size)
        for encoding in ['utf-8', 'cp949', 'euc-kr']:
            try:
                return raw.decode(encoding).strip('\x00')
            except (UnicodeDecodeError, ValueError):
                continue
        return raw.decode('latin-1').strip('\x00')

    def cyc_parser(self):
        with open(self.file_path, 'rb') as f:
            # ── PS_FILE_ID_HEADER (328 bytes) ──────────────────
            szFileID         = struct.unpack('I', f.read(4))[0]
            szFileVersion    = struct.unpack('I', f.read(4))[0]
            szCreateDateTime = self._read_str(f, 64)
            szDescription    = self._read_str(f, 128)
            szReserved       = self._read_str(f, 128)

            # print("=" * 50)
            # print(f"File ID          : {szFileID}")
            # print(f"File Version     : {szFileVersion}")
            # print(f"Creation DateTime: {szCreateDateTime}")
            # print(f"Description      : {szDescription}")
            # print("=" * 50)

            # ── PS_RECORD_FILE_HEADER ───────────────────────────
            nColumnCount     = struct.unpack('<i', f.read(4))[0]
            awColumnItem_raw = struct.unpack('<42H', f.read(2 * 42))
            awColumnItem     = list(awColumnItem_raw[:nColumnCount])  # nColumnCount개만 사용

            # print(f"Column Count     : {nColumnCount}")
            # print(f"awColumnItem     : {tuple(awColumnItem)}")
            # print(f"Record offset    : {f.tell()}")
            # print(f"awColumnItem_raw (전체 42개): {awColumnItem_raw}")
            # print(f"앞 {nColumnCount}개: {awColumnItem_raw[:nColumnCount]}")
            # print(f"16진수: {[hex(v) for v in awColumnItem_raw[:nColumnCount]]}")
            print("=" * 50)

            # awColumnItem 기반 item_struct 동적 생성
            item_struct = []
            version = Version(szFileVersion)
            RECORD_ITEM_MAP = version.record_item_map()[0]
            
            for item_id in awColumnItem:
                if item_id in RECORD_ITEM_MAP:
                    name, dtype = RECORD_ITEM_MAP[item_id]
                    # .cyc는 모든 컬럼을 float으로 저장
                    item_struct.append((name, 'f'))
                else:
                    print(f"WARNING: unknown item_id={item_id} "
                        f"(0x{item_id:02X}), treating as float")
                    item_struct.append((f"UNKNOWN_0x{item_id:02X}", "f"))
                    
            # print('item struct 결과 : ', item_struct)
            if len(item_struct) != nColumnCount:
                raise ValueError(
                    f'column count mismatch: '
                    f'header={nColumnCount}, parsed={len(item_struct)}'
                )

            fmt         = '<' + ''.join(dtype for _, dtype in item_struct)
            col_names   = [name for name, _ in item_struct]
            record_size = struct.calcsize(fmt)
            # print(f"Record size      : {record_size} bytes")

            # ── 레코드 파싱 (파일 끝까지) ──────────────────────
            raw_data = []
            while True:
                data = f.read(record_size)
                if len(data) < record_size:
                    break
                values = struct.unpack(fmt, data)
                raw_data.append(values)

            # print(f"Total records    : {len(raw_data)}")

        return (raw_data, col_names,
                szFileID, szFileVersion,
                szCreateDateTime, szDescription, szReserved)

    def data_preprocessing(self, raw_data, col_names, szFileID, szFileVersion, szCreateDateTime):
        df = pd.DataFrame(raw_data, columns=col_names)
        result = df.copy()
        result['File_ID_cyc'] = szFileID
        result['File_version_cyc'] = szFileVersion
        result['File_create_date_cyc'] = szCreateDateTime

        # ── 단위 변환 (/1000) ──────────────────────────────────
        unit_div_cols = [
            'PS_VOLTAGE', 'PS_CURRENT', 'PS_CAPACITY',
            'PS_WATT', 
            'PS_AVG_VOLTAGE', 'PS_AVG_CURRENT',
            'PS_CHARGE_CAP', 'PS_DISCHARGE_CAP',
            'PS_INTEGRAL_CAPACITY', 'PS_INTEGRAL_WATTHOUR',
            'PS_CHARGE_CC_CAP', 'PS_CHARGE_CV_CAP',
            'PS_DISCHARGE_CC_CAP', 'PS_DISCHARGE_CV_CAP'
            # 'PS_WATT_HOUR','PS_CHAR_WATTHOUR', 'PS_DISCHAR_WATTHOUR',
            # 'PS_IMPEDANCE_100MS', 'PS_IMPEDANCE_1S',
            # 'PS_IMPEDANCE_5S', 'PS_IMPEDANCE_30S', 'PS_IMPEDANCE_60S'
        ]
        for col in unit_div_cols:
            if col in result.columns:
                result[col] = result[col] / 1000

        # ── PS_DATA_SEQ 정수형 변환 ────────────────────────────
        if 'PS_DATA_SEQ' in result.columns:
            result['PS_DATA_SEQ'] = result['PS_DATA_SEQ'].astype('int')

        # ── PS_STATE, PS_RESTORED_FLAG 정수형 변환 ─────────────
        for int_col in ['PS_STATE', 'PS_RESTORED_FLAG']:
            if int_col in result.columns:
                result[int_col] = result[int_col].astype('int')

        # ── PS_TOT_TIME 생성 (포맷 변환 전에 먼저 계산!) ───────
        # PS_STEP_TIME이 아직 초(float) 단위일 때 누적합 계산
        if 'PS_STEP_TIME' in result.columns:
            result['PS_TOT_TIME'] = result['PS_STEP_TIME'].astype(float).cumsum()

        # ── 시간 포맷 변환 (초 → HH:MM:SS.xx) ─────────────────
        MAX_SECONDS = 315360000
        
        for time_col in ['PS_STEP_TIME', 'PS_CV_END_TIME', 'PS_TOT_TIME']:
            if time_col in result.columns:
                result[time_col] = (
                    pd.to_datetime(result[time_col].clip(0, MAX_SECONDS), unit='s')
                    .dt.strftime('%H:%M:%S.%f')
                    .str[:-4]
                )

        # ── REALDATE: float → int → yymmdd → datetime ─────────
        if 'PS_REALDATE' in result.columns:
            def parse_realdate(x):
                try:
                    s = str(int(float(x))).zfill(6)
                    return datetime.strptime(s, '%y%m%d')
                except Exception:
                    return pd.NaT
            result['PS_REALDATE'] = result['PS_REALDATE'].apply(parse_realdate)

        # ── REALCLOCK: float → int → HH:MM:SS.xxx ─────────────
        if 'PS_REALCLOCK' in result.columns:
            def parse_realclock(x):
                try:
                    s = str(int(float(x))).zfill(9)
                    return f"{s[:2]}:{s[2:4]}:{s[4:6]}.{s[6:]}"
                except Exception:
                    return pd.NaT
            result['PS_REALCLOCK'] = result['PS_REALCLOCK'].apply(parse_realclock)
            
        # 필요없는 컬럼 삭제
        del_col = ['PS_FARAD', 'PS_AMBIENT_TEMP', 'PS_GAS_VOLTAGE']
        for del_idx in del_col:
            if del_idx in result.columns:
                result = result.drop(del_idx, axis= 1)
        
        # 파일 정보 저장
        return result

class CtsParser:
    """
    PNE Solution .cts 바이너리 파일 파서 클래스

    .cts 파일 구조:
    ┌─────────────────────────────────┐
    │ PS_FILE_ID_HEADER   (328 bytes) │  파일 식별 정보
    ├─────────────────────────────────┤
    │ PS_TEST_FILE_HEADER (582 bytes) │  테스트 메타데이터 + wRecordItem 컬럼 정의
    ├─────────────────────────────────┤
    │ 첫 번째 StepEnd     ( 34 bytes) │  파일 시작 특수 StepEnd (크기 상이)
    │ 데이터 레코드       (136 bytes) │  34컬럼 × 4bytes
    ├─────────────────────────────────┤
    │ StepEnd             ( 44 bytes) │  이후 StepEnd (고정 44 bytes)
    │ 데이터 레코드       (136 bytes) │  34컬럼 × 4bytes
    │           ... 반복 ...          │
    └─────────────────────────────────┘

    데이터 레코드는 Step 종료 시마다 1개씩 저장됨 (Step End Record)
    """

    def __init__(self, file_path):
        """
        파라미터:
            file_path (str): 파싱할 .cts 파일 경로
        """
        self.file_path = file_path
        
    def _read_str(self, f, size):
        """
        바이트 읽어서 문자열로 디코딩 (null 제거)
        utf-8 → cp949 → euc-kr → latin-1 순으로 시도
        """
        raw = f.read(size)
        for encoding in ['utf-8', 'cp949', 'euc-kr']:
            try:
                return raw.decode(encoding).strip('\x00')
            except (UnicodeDecodeError, ValueError):
                continue
        return raw.decode('latin-1').strip('\x00')

    def parse_records(self, f, szFileVersion, fmt, record_size, item_struct, stepend_size):
        rows     = []
        stepends = []
        first    = True

        version = Version(szFileVersion)
        record_map, state_map, dataselect_map, steptype_map, mode_map, step_state_map = version.record_item_map()

        while True:
            # ── StepEnd 읽기 ──────────────────────────────────────
            if first:
                # 첫 번째 StepEnd: 34bytes
                # [0:2]=패딩, [2]=chNo, [3]=chStepNo, [4]=chState
                # [5]=chStepType, [6]=chDataSelect, [7]=cReserved
                # [8]=chGradeCode, [9]=chMode
                # [10:14]=ulIndexFrom, [14:18]=ulIndexTo
                # [18:22]=ulCurrentCycleNum, [22:26]=ulTotalCycleNum
                stepend_raw = f.read(34)
                if len(stepend_raw) < 34:
                    break

                ch_no        = stepend_raw[2]
                ch_step_no   = stepend_raw[3]
                ch_state     = stepend_raw[4]
                ch_step_type = stepend_raw[5]
                ch_mode      = stepend_raw[9]
                ul_index_from  = struct.unpack('<I', stepend_raw[10:14])[0]
                ul_index_to    = struct.unpack('<I', stepend_raw[14:18])[0]
                ul_cur_cycle   = struct.unpack('<I', stepend_raw[18:22])[0]
                ul_tot_cycle   = struct.unpack('<I', stepend_raw[22:26])[0]
                first = False
            else:
                # 두 번째 이후 StepEnd: 44bytes
                # [0:4]=패딩, [4:8]=fRealDate, [8:12]=fRealClock
                # [12]=chNo, [13]=chStepNo, [14]=chState, [15]=chStepType
                # [16]=chDataSelect, [17]=cReserved, [18]=chGradeCode, [19]=chMode
                # [20:24]=ulIndexFrom, [24:28]=ulIndexTo
                # [28:32]=ulCurrentCycleNum, [32:36]=ulTotalCycleNum
                stepend_raw = f.read(stepend_size)
                if len(stepend_raw) < stepend_size:
                    break  # 44bytes 못 읽으면 종료

                # 슬라이싱 전에 크기 재확인
                if len(stepend_raw) < 36:  # [32:36] 접근하려면 최소 36bytes 필요
                    break
                ch_no        = stepend_raw[12]
                ch_step_no   = stepend_raw[13]
                ch_state     = stepend_raw[14]
                ch_step_type = stepend_raw[15]
                ch_mode      = stepend_raw[19]
                ul_index_from = struct.unpack('<I', stepend_raw[20:24])[0]
                ul_index_to   = struct.unpack('<I', stepend_raw[24:28])[0]
                ul_cur_cycle  = struct.unpack('<I', stepend_raw[28:32])[0]
                ul_tot_cycle  = struct.unpack('<I', stepend_raw[32:36])[0]

            # ── 데이터 레코드 읽기 ────────────────────────────────
            data = f.read(record_size)
            if len(data) < record_size:
                break

            # StepEnd + Record 둘 다 성공했을 때만 추가
            stepends.append({
                'chNo'             : ch_no,
                'chStepNo'         : ch_step_no,
                'chState'          : state_map.get(ch_state),
                'chStepType'       : steptype_map.get(ch_step_type),
                'Mode'             : mode_map.get(ch_mode),
                'ulIndexFrom'      : ul_index_from,
                'ulIndexTo'        : ul_index_to,
                'ulCurrentCycleNum': ul_cur_cycle,
                'ulTotalCycleNum'  : ul_tot_cycle,
            })
            rows.append(struct.unpack(fmt, data))

        return rows, stepends


    def get_stepend_size(self, version):
        """
        버전별 StepEnd 크기 반환 (두 번째 이후 StepEnd 기준)

        실측 확인:
            - 첫 번째 StepEnd : 34 bytes (parse_records에서 별도 처리)
            - 두 번째 이후    : 44 bytes = 4(패딩) + 4(REALDATE) + 4(REALCLOCK) + 32(메타)
        """
        stepend_size_map = {
            4101      : 44,
            4102      : 44,
            4103      : 44,
            8193      : 44,
            8194      : 44,
            8195      : 44,
            8196      : 44,
            12289     : 44,
            12290     : 44,
            12291     : 44,
            16385     : 44,
            16386     : 44,
            '4101_GAS': 44,
        }
        size = stepend_size_map.get(version)
        if size is None:
            raise ValueError(f"StepEnd size unknown for version: {version}")
        return size

    def build_struct_format(self, item_struct):
        """
        item_struct로부터 struct.unpack용 포맷 문자열과 레코드 바이트 크기 계산

        파라미터:
            item_struct: [(컬럼명, 타입문자), ...] 리스트
                         타입문자: "f"(float 4bytes), "I"(unsigned int 4bytes)

        반환:
            fmt         : struct 포맷 문자열 (ex: '<fffIffff...')
                          '<' = little-endian
            record_size : 레코드 1개의 전체 바이트 크기
        """
        fmt = '<' + ''.join(dtype for _, dtype in item_struct)
        size = struct.calcsize(fmt)
        # print(f"Calculated record byte size: {size}")
        return fmt, size

    def cts_parser(self):
        with open(self.file_path, 'rb') as f:
            # ── PS_FILE_ID_HEADER (328 bytes) ──────────────────
            szFileID         = struct.unpack('I', f.read(4))[0]
            szFileVersion    = struct.unpack('I', f.read(4))[0]
            szCreateDateTime = self._read_str(f, 64)
            szDescription    = self._read_str(f, 128)
            szReserved       = self._read_str(f, 128)

            # ── PS_TEST_FILE_HEADER (582 bytes) ────────────────
            szStartTime  = self._read_str(f, 64)
            szEndTime    = self._read_str(f, 64)
            szSerial     = self._read_str(f, 64)
            szUserID     = self._read_str(f, 32)
            szDescript   = self._read_str(f, 128)
            szTrayNo     = self._read_str(f, 64)
            szBuff       = self._read_str(f, 64)
            nRecordSize  = struct.unpack('<I', f.read(4))[0]

            wRecordItems_raw = struct.unpack('<49H', f.read(98))
            wRecordItems     = [v for v in wRecordItems_raw if v != 0]

            # print("=" * 50)
            # print(f"File ID       : {szFileID}")
            # print(f"File Version  : {szFileVersion}")
            # print(f"Start Time    : {szStartTime}")
            # print(f"End Time      : {szEndTime}")
            # print(f"Serial        : {szSerial}")
            # print(f"Record Size   : {nRecordSize}")
            # print(f"wRecordItem   : {tuple(wRecordItems)}")
            # print(f"Record offset : {f.tell()}")
            # print("=" * 50)

            # 버전 확인 및 RECORD_ITEM_MAP 로드
            version         = Version(szFileVersion)
            RECORD_ITEM_MAP = version.record_item_map()[0]

            # wRecordItem 기반 item_struct 동적 생성
            item_struct = []
            for item_id in wRecordItems:
                if item_id in RECORD_ITEM_MAP:
                    item_struct.append(RECORD_ITEM_MAP[item_id])
                else:
                    print(f"WARNING: unknown item_id={item_id} "
                        f"(0x{item_id:02X}), treating as float")
                    item_struct.append((f"UNKNOWN_0x{item_id:02X}", "f"))

            if len(item_struct) != nRecordSize:
                raise ValueError(
                    f'column count mismatch: '
                    f'header={nRecordSize}, parsed={len(item_struct)}'
                )

            col_names        = [name for name, _ in item_struct]
            stepend_size     = self.get_stepend_size(szFileVersion)
            fmt, record_size = self.build_struct_format(item_struct)

            # ← 인자 순서 수정 + stepends 함께 받기
            rows, stepends = self.parse_records(
                f, szFileVersion, fmt, record_size, item_struct, stepend_size
            )
            # print(f"Total records  : {len(rows)}")
            # print(f"Total stepends : {len(stepends)}")

        return (rows, stepends, col_names,
                szFileID, szFileVersion, szStartTime,
                szCreateDateTime, szDescription, szReserved)

    def data_preprocessing(self, raw_data, col_names, szFileID, szFileVersion, szStartTime, szCreateDateTime,stepends=None):
        # raw_data가 tuple 리스트이므로 columns로 DataFrame 생성
        df = pd.DataFrame(raw_data, columns=col_names)
        result = df.copy()
        result['File_ID_cts'] = szFileID
        result['File_version_cts'] = szFileVersion
        result['Start_time_cts'] = szStartTime
        result['File_create_date_cts'] = szCreateDateTime
        
        # ── StepEnd 정보 추가 ──────────────────────────────────
        # .cts는 레코드 1개 = StepEnd 1개로 1:1 대응
        if stepends and len(stepends) == len(result):
            result.insert(0, 'Mode', [s['Mode'] for s in stepends])
            result.insert(0, 'ulTotalCycleNum',    [s['ulTotalCycleNum']    for s in stepends])
            result.insert(0, 'ulCurrentCycleNum',  [s['ulCurrentCycleNum']  for s in stepends])
            result.insert(0, 'chStepType',[s['chStepType']for s in stepends])
            result.insert(0, 'ulIndexTo',   [s['ulIndexTo']   for s in stepends])
            result.insert(0, 'ulIndexFrom', [s['ulIndexFrom'] for s in stepends])
            result.insert(0, 'chStepNo',  [s['chStepNo']  for s in stepends])
            result.insert(0, 'chNo',      [s['chNo']      for s in stepends])
        elif stepends and len(stepends) != len(result):
            print(f"WARNING: stepends({len(stepends)})와 "
                f"rows({len(result)}) 수가 불일치 → 매핑 스킵")

        # 단위 변환 (/1000)
        unit_div_cols = [
            'PS_VOLTAGE', 'PS_CURRENT', 'PS_CAPACITY',
            'PS_WATT', 'PS_WATT_HOUR',
            'PS_AVG_VOLTAGE', 'PS_AVG_CURRENT',
            'PS_CHARGE_CAP', 'PS_DISCHARGE_CAP',
            'PS_CHAR_WATTHOUR', 'PS_DISCHAR_WATTHOUR',
            'PS_INTEGRAL_CAPACITY', 'PS_INTEGRAL_WATTHOUR',
            'PS_CHARGE_CC_CAP', 'PS_CHARGE_CV_CAP',
            'PS_DISCHARGE_CC_CAP', 'PS_DISCHARGE_CV_CAP',
            'PS_IMPEDANCE_100MS', 'PS_IMPEDANCE_1S',
            'PS_IMPEDANCE_5S', 'PS_IMPEDANCE_30S', 'PS_IMPEDANCE_60S',
        ]
        for col in unit_div_cols:
            if col in result.columns:
                result[col] = result[col] / 1000

        # 시간 포맷 변환 (초 → HH:MM:SS.xx)
        for time_col in ['PS_STEP_TIME', 'PS_CV_END_TIME', 'PS_TOT_TIME']:
            if time_col in result.columns:
                result[time_col] = (
                    pd.to_datetime(result[time_col], unit='s')
                    .dt.strftime('%H:%M:%S.%f')
                    .str[:-4]
                )

        # REALDATE: float → StartTime 기준 절대 datetime
        if 'PS_REALDATE' in result.columns:
            def parse_realdate(x):
                try:
                    val = float(x)
                    if val == 0:
                        return pd.NaT
                    s = str(int(val)).zfill(6)
                    return datetime.strptime(s, '%y%m%d')
                except Exception:
                    return pd.NaT
            result['PS_REALDATE'] = result['PS_REALDATE'].apply(parse_realdate)

        # REALCLOCK: float → HH:MM:SS.xxx
        if 'PS_REALCLOCK' in result.columns:
            def parse_realclock(x):
                try:
                    val = float(x)
                    if val == 0:
                        return pd.NaT
                    s = str(int(val)).zfill(9)
                    return f"{s[:2]}:{s[2:4]}:{s[4:6]}.{s[6:]}"
                except Exception:
                    return pd.NaT
            result['PS_REALCLOCK'] = result['PS_REALCLOCK'].apply(parse_realclock)

        return result
    
class SchParser:
    """
    PNE Solution .sch 바이너리 파일 파서 클래스

    ┌─────────────────────────────────────────────────────────┐
    │                   .sch 파일 전체 구조                    │
    ├──────────────────────────┬──────────────────────────────┤
    │ PS_FILE_ID_HEADER        │  328 bytes                   │
    ├──────────────────────────┼──────────────────────────────┤
    │ FILE_TEST_INFORMATION ×2 │  784 bytes (392 × 2)        │
    ├──────────────────────────┼──────────────────────────────┤
    │ FILE_CELL_CHECK_PARAM    │  104 bytes + 패딩 544 bytes  │
    ├──────────────────────────┼──────────────────────────────┤
    │ FILE_STEP_CONDITION × N  │  파일마다 크기 상이           │
    │  (파일 끝까지 반복)       │  동적 탐지로 크기 결정        │
    └──────────────────────────┴──────────────────────────────┘

    StepNo 관계:
        - 파일 맨 앞에 항상 Cycle 스텝 1개가 존재하나 파일에 저장되지 않음
        - 파일의 CYCLE 스텝 자체가 CSV의 Cycle 스텝에 해당
        - csvStepNo: 맨 앞 Cycle 삽입 후 1부터 순서대로 부여
    """

    STEP_TYPE_MAP = {
        0x01: 'CHARGE',
        0x02: 'DISCHARGE',
        0x03: 'REST',
        0x04: 'OCV',
        0x05: 'IMPEDANCE',
        0x06: 'END',
        0x07: 'CYCLE',
        0x08: 'LOOP',
        0x09: 'PATTERN',
        0x0A: 'BALANCE',
    }

    STEP_MODE_MAP = {
        0x01: 'CCCV',
        0x02: 'CC',
        0x03: 'CV',
        0x04: 'DCIMP',
        0x05: 'ACIMP',
        0x06: 'CP',
        0x07: 'PUSE',
        0x08: 'CR',
    }

    VALID_STEP_TYPES = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A}

    def __init__(self, file_path):
        self.file_path = file_path
        with open(file_path, 'rb') as f:
            self._raw = f.read()
        self._file_size = len(self._raw)
        

    def _read_str(self, f, size):
        """
        바이트 읽어서 문자열로 디코딩 (null 제거)
        utf-8 → cp949 → euc-kr → latin-1 순으로 시도
        """
        raw = f.read(size)
        for encoding in ['utf-8', 'cp949', 'euc-kr']:
            try:
                return raw.decode(encoding).strip('\x00')
            except (UnicodeDecodeError, ValueError):
                continue
        return raw.decode('latin-1').strip('\x00')

    def _detect_step_size(self, current_offset, current_step_no):
        """
        현재 스텝 offset에서 다음 스텝 시작까지의 거리를 동적으로 탐지

        탐지 조건:
            - chStepNo == current_step_no + 1
            - chReserved[3] == 0x000000
            - chType이 유효한 값

        파라미터:
            current_offset  : 현재 스텝 시작 offset
            current_step_no : 현재 스텝 번호

        반환:
            step_size (int): 현재 스텝 크기 (bytes)
                             다음 스텝을 못 찾으면 파일 끝까지
        """
        next_step_no = current_step_no + 1
        raw = self._raw

        for i in range(4, self._file_size - current_offset - 11, 4):
            pos     = current_offset + i
            sno     = raw[pos]
            res     = raw[pos+1:pos+4]
            ch_type = raw[pos+8]
            if (sno == next_step_no
                    and res == b'\x00\x00\x00'
                    and ch_type in self.VALID_STEP_TYPES):
                return i

        return self._file_size - current_offset

    def _parse_file_id_header(self, f):
        """PS_FILE_ID_HEADER 파싱 (328 bytes)"""
        return {
            'nFileID'          : struct.unpack('<I', f.read(4))[0],  # UINT  4 bytes
            'nFileVersion'     : struct.unpack('<I', f.read(4))[0],  # UINT  4 bytes
            'szCreateDateTime' : self._read_str(f, 64),              # char  64 bytes
            'szDescription'    : self._read_str(f, 128),             # char  128 bytes
            'szReserved'       : self._read_str(f, 128),             # char  128 bytes
        }

    def _parse_file_test_information(self, f):
        """FILE_TEST_INFORMATION 파싱 (392 bytes), 2회 반복"""
        return {
            'lID'           : struct.unpack('<l', f.read(4))[0],  # LONG  4 bytes
            'lType'         : struct.unpack('<l', f.read(4))[0],  # LONG  4 bytes
            'szName'        : self._read_str(f, 128),             # char  128 bytes
            'szDescription' : self._read_str(f, 128),             # char  128 bytes
            'szCreator'     : self._read_str(f, 64),              # char  64 bytes
            'szModifiedTime': self._read_str(f, 64),              # char  64 bytes
        }

    def _parse_file_cell_check_param(self, f, version):
        """
        FILE_CELL_CHECK_PARAM 파싱
        실제 파일 분석으로 확인된 구조:
            0x458~0x46F: fMaxVoltage~lTrickleTime (28 bytes)
            0x470~0x483: 미지 패딩 16 bytes
            0x484      : nMaxFaultNo 4 bytes
            0x488~0x4BB: 패딩 52 bytes
            0x4BC      : bPreTest 4 bytes
            0x4C0~0x6DF: 패딩 544 bytes → STEP_DATA 시작(0x6E0)
        """
        if (version == 0x00010007) | (version == 0x00010004):
            data = {
                'fMaxVoltage'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fMinVoltage'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fMaxCurrent'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fOCVLimitVal'     : struct.unpack('<f', f.read(4))[0],        # 65543은 fOCVLimitVal
                'TrickleCurrent'     : struct.unpack('<f', f.read(4))[0],        # 65543은 fTrickleCurrent
                'fDeltaVoltage': struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'lTrickleTime' : struct.unpack('<L', f.read(4))[0],        # ULONG  4 bytes
            }
            f.read(16)  # 미지 패딩 16 bytes
            data['nMaxFaultNo'] = struct.unpack('<i', f.read(4))[0]        # int    4 bytes
            f.read(52)  # 패딩 52 bytes
            data['bPreTest']    = bool(struct.unpack('<i', f.read(4))[0])  # BOOL   4 bytes
            f.read(544) # 패딩 544 bytes → 0x6E0까지
        else:
            data = {
                'fMaxVoltage'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fMinVoltage'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fMaxCurrent'  : struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'fVrefVal'     : struct.unpack('<f', f.read(4))[0],        # 65543은 fOCVLimitVal
                'fIrefVal'     : struct.unpack('<f', f.read(4))[0],        # 65543은 fTrickleCurrent
                'fDeltaVoltage': struct.unpack('<f', f.read(4))[0],        # float  4 bytes
                'lTrickleTime' : struct.unpack('<L', f.read(4))[0],        # ULONG  4 bytes
            }
            f.read(16)  # 미지 패딩 16 bytes
            data['nMaxFaultNo'] = struct.unpack('<i', f.read(4))[0]        # int    4 bytes
            f.read(52)  # 패딩 52 bytes
            data['bPreTest']    = bool(struct.unpack('<i', f.read(4))[0])  # BOOL   4 bytes
            f.read(544) # 패딩 544 bytes → 0x6E0까지
        return data

    def _parse_file_grade(self, f):
        """
        FILE_GRADE 파싱 (100 bytes)
            long  lGradeItem        4 bytes
            BYTE  chTotalGrade      1 byte
            패딩                    3 bytes
            float faValue1[10]     40 bytes
            float faValue2[10]     40 bytes
            char  aszGradeCode[10] 10 bytes
            패딩                    2 bytes
        """
        data = {
            'lGradeItem'  : struct.unpack('<l', f.read(4))[0],         # long  4 bytes
            'chTotalGrade': struct.unpack('<B', f.read(1))[0],         # BYTE  1 byte
        }
        f.read(3)  # 패딩 3 bytes
        data['faValue1']     = list(struct.unpack('<10f', f.read(40))) # float[10] 40 bytes
        data['faValue2']     = list(struct.unpack('<10f', f.read(40))) # float[10] 40 bytes
        data['aszGradeCode'] = self._read_str(f, 10)                   # char[10]  10 bytes
        f.read(2)  # 패딩 2 bytes
        return data

    def _parse_step_common(self, f):
        """
        FILE_STEP_CONDITION 공통 기본 구조 파싱
        모든 스텝 타입의 공통 필드

        반환:
            data (dict): 파싱된 필드
            None: chStepNo=0 또는 파일 끝
        """
        start_offset = f.tell()

        peek = f.read(1)
        if not peek:
            return None
        f.seek(start_offset)

        # ── 기본 식별 필드 (8 bytes) ───────────────────────────
        chStepNo  = struct.unpack('<B', f.read(1))[0]  # BYTE  1 byte
        if chStepNo == 0:
            return None
        f.read(3)                                       # chReserved[3] 3 bytes
        nProcType = struct.unpack('<i', f.read(4))[0]  # int   4 bytes

        # ── chType / chMode (4 bytes) ──────────────────────────
        chType = struct.unpack('<B', f.read(1))[0]     # BYTE  1 byte
        chMode = struct.unpack('<B', f.read(1))[0]     # BYTE  1 byte
        f.read(2)                                       # wReserved1 2 bytes

        data = {
            'chStepNo'  : chStepNo,
            'nProcType' : nProcType,
            'chType'    : chType,
            'chTypeName': self.STEP_TYPE_MAP.get(chType, f'UNKNOWN(0x{chType:02X})'),
            'chMode'    : chMode,
            'chModeName': self.STEP_MODE_MAP.get(chMode, 'NONE'),
        }

        # ── 종료 조건 (36 bytes) ───────────────────────────────
        data['fVref']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fIref']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndTime']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndCVTime']= struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndV']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndI']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndC']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndDV']    = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndDI']    = struct.unpack('<f', f.read(4))[0]  # float 4 bytes

        # ── 루프 정보 (40 bytes) ───────────────────────────────
        data['nLoopInfoGoto']        = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoCycle']       = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndTGoto']    = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoCVEndTGoto']  = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndVGoto']    = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndIGoto']    = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndCGoto']    = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndTempGoto'] = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nLoopInfoEndSocGoto']  = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes
        data['nGotoStepID']          = struct.unpack('<I', f.read(4))[0]  # UINT 4 bytes

        # ── 온도 설정 (4 bytes) ────────────────────────────────
        data['tempType'] = struct.unpack('<b', f.read(1))[0]  # char 1 byte
        data['tempDir']  = struct.unpack('<b', f.read(1))[0]  # char 1 byte
        f.read(2)  # 패딩 2 bytes

        # ── 리밋 설정 (48 bytes) ───────────────────────────────
        data['fVLimitHigh']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fVLimitLow']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fILimitHigh']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fILimitLow']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fCLimitHigh']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fCLimitLow']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fImpLimitHigh']= struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fImpLimitLow'] = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDeltaTime']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDeltaTime1']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDeltaV']      = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDeltaI']      = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['bGrade']       = bool(struct.unpack('<i', f.read(4))[0])  # BOOL 4 bytes

        # ── FILE_GRADE (100 bytes) ─────────────────────────────
        data['sGrading_Val'] = self._parse_file_grade(f)

        # ── 비교 설정 (72 bytes) ───────────────────────────────
        data['fCompVLow']  = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes
        data['fCompVHigh'] = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes
        data['fCompTimeV'] = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes
        data['fCompILow']  = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes
        data['fCompIHigh'] = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes
        data['fCompTimeI'] = list(struct.unpack('<3f', f.read(12)))  # float[3] 12 bytes

        # ── 패턴/시간/리포트 설정 (92 bytes) ──────────────────
        data['fPatternMinVal'] = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fPatternMaxVal'] = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fStartT']        = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndT']          = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fReportV']       = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fReportI']       = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fReportTime']    = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fAutoTempLow']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fAutoTempHigh']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fCapaVoltage1']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fCapaVoltage2']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDCRStartTime']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fDCREndTime']    = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fLCStartTime']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fLCEndTime']     = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['lRange']         = struct.unpack('<l', f.read(4))[0]  # LONG  4 bytes
        data['fReportTemp']    = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fSocRate']       = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndW']          = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fEndWh']         = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fHighLimitTemp'] = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fLowLimitTemp']  = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fTref']          = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['nType']          = struct.unpack('<h', f.read(2))[0]  # short 2 bytes
        data['nMode']          = struct.unpack('<h', f.read(2))[0]  # short 2 bytes
        data['fMaxCapacity']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes
        data['fRenewalTime']   = struct.unpack('<f', f.read(4))[0]  # float 4 bytes

        # ── 테이블/예약 필드 (72 bytes) ────────────────────────
        data['ocvTableRow']   = struct.unpack('<b', f.read(1))[0]        # char      1 byte
        data['ocvTableCol']   = struct.unpack('<b', f.read(1))[0]        # char      1 byte
        data['powerTableRow'] = struct.unpack('<b', f.read(1))[0]        # char      1 byte
        data['powerTableCol'] = struct.unpack('<b', f.read(1))[0]        # char      1 byte
        data['fReserved']     = list(struct.unpack('<17f', f.read(68)))  # float[17] 68 bytes

        # ── 기타 제어 플래그 (8 bytes) ─────────────────────────
        data['cNotUseTempWait'] = struct.unpack('<B', f.read(1))[0]  # uchar 1 byte
        f.read(3)                                                      # cReserved[3]
        data['bUseActualCapa']  = struct.unpack('<B', f.read(1))[0]  # BYTE  1 byte
        data['bUseDataStepNo']  = struct.unpack('<B', f.read(1))[0]  # BYTE  1 byte
        data['bEndStepSave']    = struct.unpack('<B', f.read(1))[0]  # BYTE  1 byte
        data['bInitIntegralCap']= struct.unpack('<B', f.read(1))[0]  # BYTE  1 byte

        # ── 시뮬레이션/루프/예약 (112 bytes) ──────────────────
        data['szSimulationFile'] = self._read_str(f, 64)                   # char[64]  64 bytes
        data['nLoopInfoGotoCnt'] = struct.unpack('<I', f.read(4))[0]       # UINT       4 bytes
        data['bComplete']        = struct.unpack('<B', f.read(1))[0]       # BYTE       1 byte
        f.read(3)                                                            # bReserved[3]
        data['lReserved']        = list(struct.unpack('<10l', f.read(40))) # long[10]  40 bytes

        return data

    def _parse_file_step_condition(self, f):
        """
        FILE_STEP_CONDITION 파싱
        다음 스텝 시작 위치를 동적으로 탐지해서 현재 스텝 크기 결정
        """
        start_offset = f.tell()

        data = self._parse_step_common(f)
        if data is None:
            return None

        total_size = self._detect_step_size(start_offset, data['chStepNo'])
        parsed     = f.tell() - start_offset
        remaining  = total_size - parsed

        if remaining > 0:
            f.read(remaining)
        elif remaining < 0:
            print(f"  WARNING: 파싱 크기 초과 {-remaining} bytes "
                  f"(offset=0x{f.tell():04X}, StepNo={data['chStepNo']})")

        return data

    def sch_parser(self):
        """
        .sch 파일 전체 파싱

        반환:
            file_id_header   : PS_FILE_ID_HEADER dict
            test_info_1      : FILE_TEST_INFORMATION dict (1번째)
            test_info_2      : FILE_TEST_INFORMATION dict (2번째)
            cell_check_param : FILE_CELL_CHECK_PARAM dict
            steps            : FILE_STEP_CONDITION list of dict
        """
        with open(self.file_path, 'rb') as f:

            # ── PS_FILE_ID_HEADER (328 bytes) ──────────────────
            file_id_header = self._parse_file_id_header(f)

            # ── FILE_TEST_INFORMATION × 2 (784 bytes) ──────────
            test_info_1 = self._parse_file_test_information(f)
            test_info_2 = self._parse_file_test_information(f)

            # ── FILE_CELL_CHECK_PARAM + 패딩 (0x458~0x6DF) ─────
            version = file_id_header.get('nFileVersion')
            cell_check_param = self._parse_file_cell_check_param(f, version)

            # print("=" * 60)
            # print(f"File ID         : {file_id_header['nFileID']}")
            # print(f"File Version    : {file_id_header['nFileVersion']}")
            # print(f"Create Time     : {file_id_header['szCreateDateTime']}")
            # print(f"Description     : {file_id_header['szDescription']}")
            # print(f"Test Name       : {test_info_2['szName']}")
            # print(f"Modified Time   : {test_info_2['szModifiedTime']}")
            # print(f"Max Voltage     : {cell_check_param['fMaxVoltage']} mV")
            # print(f"Min Voltage     : {cell_check_param['fMinVoltage']} mV")
            # print(f"Max Current     : {cell_check_param['fMaxCurrent']} mA")
            # print(f"Delta Voltage   : {cell_check_param['fDeltaVoltage']}")
            # print(f"Max Fault No    : {cell_check_param['nMaxFaultNo']}")
            # print(f"Pre Test        : {cell_check_param['bPreTest']}")
            # print(f"Step offset     : 0x{f.tell():04X}")
            # print("=" * 60)

            # ── FILE_STEP_CONDITION × N (파일 끝까지) ──────────
            steps = []
            while True:
                step = self._parse_file_step_condition(f)
                if step is None:
                    break
                steps.append(step)
            #     print(f"  Step {step['chStepNo']:2d} | "
            #           f"Type={step['chTypeName']:<12} | "
            #           f"Mode={step['chModeName']:<6} | "
            #           f"fVref={step['fVref']:8.3f} | "
            #           f"fIref={step['fIref']:8.3f} | "
            #           f"fEndTime={step['fEndTime']:10.2f} | "
            #           f"fEndV={step['fEndV']:7.3f}")

            # print("=" * 60)
            # print(f"Total steps parsed: {len(steps)}")

        return file_id_header, test_info_1, test_info_2, cell_check_param, steps

    def data_preprocessing(self, test_info_1, test_info_2, cell_check_param, steps):
        """
        스텝 데이터 단위 변환 및 CSV StepNo 복원

        단위 변환 (/1000):
            mV → V : fVref, fEndV, fVLimitHigh, fVLimitLow
            mA → A : fIref, fEndI, fILimitHigh, fILimitLow
            mAh→ Ah: fCLimitHigh, fCLimitLow

        fEndTime: 초 → HH:MM:SS.xx 형식

        csvStepNo 복원:
            파일 맨 앞에 항상 Cycle 1개가 존재하나 파일에 저장되지 않으므로
            맨 앞에 Cycle 행을 삽입하고 1부터 순서대로 csvStepNo 부여
            파일의 CYCLE 스텝은 그대로 CSV의 Cycle 스텝에 해당
        """
        df = pd.DataFrame(steps)
        result = df.copy() 
        cell_check_param_col = list(cell_check_param.keys())
        cell_check_param_col_mod = []
        result['Reseacher'] = test_info_1.get('szName')
        result['Test_name'] = test_info_2.get('szName')
        result['Description_sch'] = test_info_2.get('szDescription')
        for cell_idx in cell_check_param_col:
            result[cell_idx] = cell_check_param.get(cell_idx)
            if result[cell_idx].dtype != float:
                cell_check_param_col_mod.append(cell_idx)
        

        # ── 단위 변환 (/1000) ──────────────────────────────────
        unit_div_cols = [
            'fVref', 'fIref',
            'fEndV', 'fEndI',
            'fVLimitHigh', 'fVLimitLow',
            'fILimitHigh', 'fILimitLow',
            'fCLimitHigh', 'fCLimitLow',
        ]
        for col in unit_div_cols:
            if col in result.columns:
                result[col] = result[col] / 1000
        for col2 in cell_check_param_col:
            if col2 in result.columns:
                result[col2] = result[col2] / 1000

        # ── fEndTime: 초 → HH:MM:SS.xx ────────────────────────
        if 'fEndTime' in result.columns:
            def seconds_to_hhmmss(sec):
                try:
                    sec       = float(sec)
                    total_sec = int(sec)
                    frac      = round((sec - total_sec) * 100)
                    hh        = total_sec // 3600
                    mm        = (total_sec % 3600) // 60
                    ss        = total_sec % 60
                    return f"{hh:02d}:{mm:02d}:{ss:02d}.{frac:02d}"
                except Exception:
                    return str(sec)
            result['fEndTime'] = result['fEndTime'].apply(seconds_to_hhmmss)

        # ── CSV StepNo 복원 + 맨 앞 Cycle 행 삽입 ─────────────
        cycle_row = {col: None for col in result.columns}
        cycle_row['chTypeName'] = 'CYCLE'
        cycle_row['chModeName'] = 'NONE'

        result_df = pd.concat(
            [pd.DataFrame([cycle_row]), result],
            ignore_index=True
        )

        # chStepNo 재부여: 1부터 순서대로
        result_df['chStepNo'] = range(1, len(result_df) + 1)

        # csvStepNo 1부터 순서대로 부여
        result_df.insert(0, 'csvStepNo', range(1, len(result_df) + 1))
        # [['chStepNo', 'chTypeName', 'chModeName','fVref', 'fIref','fEndTime', 'fEndV', 'fEndI', 'fEndC']]
        return result_df[['Test_name','Reseacher', 'Description_sch', 'chStepNo', 'chTypeName', 'chModeName','fVref', 'fIref','fEndTime', 'fEndV', 'fEndI', 'fEndC']]

class cyc_cts_sch_comb:
    def __init__(self, cyc_file_path, cts_file_path, sch_file_path):
        self.cyc_file_path = cyc_file_path
        self.cts_file_path = cts_file_path
        self.sch_file_path = sch_file_path
    
    def load_data(self):
        cyc_parser = CycParser(self.cyc_file_path)
        (cyc_raw_data, cyc_col_names, cyc_szFileID, cyc_szFileVersion, cyc_szCreateDateTime, cyc_szDescription, cyc_szReserved) = cyc_parser.cyc_parser()
        cyc_df = cyc_parser.data_preprocessing(cyc_raw_data, cyc_col_names, cyc_szFileID, cyc_szFileVersion, cyc_szCreateDateTime)
        
        cts_parser = CtsParser(self.cts_file_path)
        (cts_rows, cts_stepends, cts_col_names, cts_szFileID, cts_szFileVersion, cts_szStartTime, cts_szCreateDateTime, cts_szDescription, cts_szReserved) = cts_parser.cts_parser()
        cts_result = cts_parser.data_preprocessing(cts_rows, cts_col_names, cts_szFileID, cts_szFileVersion, cts_szStartTime, cts_szCreateDateTime, cts_stepends)
        
        sch_parser = SchParser(self.sch_file_path)
        file_id_header, test_info_1, test_info_2, cell_check_param, steps = sch_parser.sch_parser()
        sch_df = sch_parser.data_preprocessing(test_info_1, test_info_2, cell_check_param, steps)
        
        return cyc_df, cts_result, sch_df
    


    # ── [1] calc_dqdv 메서드 ───────────────────────────────────────
    # cyc_cts_sch_comb 클래스 안에 추가

    def calc_dqdv(self, df, window=10):
        """
        dQ/dV 계산 + Moving Average smoothing
        cyc_result, cts_result 둘 다 적용 가능

        파라미터:
            df     : cyc_result 또는 cts_result DataFrame
            window : Moving average 윈도우 크기 (기본 10)

        반환:
            df : dQdV 컬럼 추가된 DataFrame
        """
        result = df.copy()
        result['dQdV'] = np.nan
    
        # 필수 컬럼 확인
        required = ['Capacity', 'Voltage', 'chNo', 'ulCurrentCycleNum', 'chStepType']
        missing  = [c for c in required if c not in result.columns]
        if missing:
            print(f"  ⚠️ dQ/dV 계산 스킵 - 컬럼 없음: {missing}")
            return result
    
        group_cols = ['chNo', 'ulCurrentCycleNum', 'chStepType']
    
        for keys, group in result.groupby(group_cols):
            idx = group.index
    
            Q = pd.to_numeric(group['Capacity'], errors='coerce').values
            V = pd.to_numeric(group['Voltage'],  errors='coerce').values
    
            if len(Q) < 2:
                continue
    
            # dQ/dV 계산
            dQ = np.diff(Q, prepend=Q[0])
            dV = np.diff(V, prepend=V[0])
    
            # dV가 0에 가까운 경우 NaN 처리
            with np.errstate(divide='ignore', invalid='ignore'):
                dqdv = np.where(np.abs(dV) > 1e-6, dQ / dV, np.nan)
    
            # Moving average smoothing
            dqdv_series = pd.Series(dqdv)
            dqdv_smooth = dqdv_series.rolling(
                window=window,
                center=True,
                min_periods=1
            ).mean().values
    
            result.loc[idx, 'dQdV'] = dqdv_smooth
    
        return result

    
    def comb_data_preprocessing(self):
        cyc_df, cts_df, sch_df = self.load_data()
        cyc_result = cyc_df.reset_index(drop = True).copy()
        cts_result = cts_df.reset_index(drop = True).copy()
        
        # cyc_df, sch_df 조합으로 스케줄 조건 추가하기
        type_change = {"PS_STEP_NONE":"NONE", "PS_STEP_CHARGE":"CHARGE","PS_STEP_DISCHARGE":"DISCHARGE","PS_STEP_REST":"REST","PS_STEP_OCV":"OCV", "PS_STEP_IMPEDANCE":"IMPEDANCE", "PS_STEP_END":"END", "PS_STEP_ADV_CYCLE":"ADV_CYCLE", "PS_STEP_LOOP": "LOOP", "PS_STEP_PATTERN":"PATTERN", "PS_STEP_BALANCE":"BALANCE", "PS_STEP_USERMAP":"USERMAP"}
        for k, v in type_change.items():
            cts_result['chStepType'] = cts_result['chStepType'].replace(k, v)
        cts_result = cts_result.merge(sch_df, left_on = ['chStepNo', 'chStepType'], right_on = ['chStepNo','chTypeName'], how = 'left')        
        
        # cts와 cyc 조합하기
        cyc_seq = cyc_result['PS_DATA_SEQ'] - 1
        cyc_result['cyc_file_path'] = os.path.split(self.cyc_file_path)[-1]
        cts_result['cts_file_path'] = os.path.split(self.cts_file_path)[-1]
        
        if '/TEST' in self.cyc_file_path:
            cyc_result['TEST_no'] = self.cyc_file_path[self.cyc_file_path.find('/TEST') + 1 : self.cyc_file_path.find('/TEST') + 7]
            cts_result['TEST_no'] = self.cts_file_path[self.cts_file_path.find('/TEST') + 1 : self.cts_file_path.find('/TEST') + 7]
        else:
            cyc_result['TEST_no'] = np.nan
            cts_result['TEST_no'] = np.nan

        # cts_result의 범위 정보로 인덱스 매핑 테이블 생성
        rows = []
        for idx, row in cts_result.iterrows():
            mask = (cyc_seq >= row['ulIndexFrom']) & (cyc_seq <= row['ulIndexTo'])
            rows.append(mask)

        # 컬럼 한번에 assign
        mapping_cols = ['chNo', 'chStepType', 'ulCurrentCycleNum', 'ulTotalCycleNum',
                    'fVref', 'fIref', 'fEndTime', 'fEndV', 'fEndI', 'fEndC',
                    'Test_name', 'Reseacher', 'Description_sch']

        for idx, mask in enumerate(rows):
            cyc_result.loc[cyc_seq[mask].index, mapping_cols] = cts_result.loc[idx, mapping_cols].values
            
        cyc_result = self.column_rename(cyc_result)
        cts_result = self.column_rename(cts_result)

        cyc_result = self.calc_dqdv(cyc_result, window=10)    
        cts_result = self.calc_dqdv(cts_result, window=10)    
            
        return cyc_result, cts_result, sch_df
    
    def column_rename(self, df):
        result = df.copy()
        change_columns = {'PS_DATA_SEQ':'Sequence', 'PS_STEP_TIME':'Steptime', 'PS_CV_END_TIME':'CV_end_time', 'PS_TOT_TIME_CARRY':'TOT_TIME_CARRY', 'PS_VOLTAGE':'Voltage', 'PS_CURRENT':'Current', 'PS_CAPACITY':'Capacity', 'PS_INTEGRAL_CAPACITY':'Integral_capacity', 'PS_CHARGE_CAP':'Charge_capacity', 'PS_DISCHARGE_CAP':'Discharge_capacity',
         'PS_WATT_HOUR':'Watt_hour', 'PS_INTEGRAL_WATTHOUR':'Integral_watthour', 'PS_CHAR_WATTHOUR':'Charge_watthour', 'PS_DISCHAR_WATTHOUR':'Discharge_watthour', 'PS_AVG_CURRENT':'Average_current', 'PS_AVG_VOLTAGE':'Average_voltage', 'PS_TEMPERATURE':'Temperature', 'PS_IMPEDANCE':'Impedance', 'PS_WATT':'Watt', 'PS_CAPACITY_SUM':'Capacity_sum',
         'PS_WATTHOUR_SUM':'Watthour_sum', 'PS_CHAMBER_TEMPERATURE':'Chamber_temperature', 'PS_TEMPERATURE2':'Temperature2', 'PS_CHARGE_CC_CAP':'Charge_CC_capacity', 'PS_CHARGE_CV_CAP':'Charge_CV_capacity', 'PS_DISCHARGE_CC_CAP':'Discharge_CC_capacity', 'PS_DISCHARGE_CV_CAP':'Discharge_CV_capacity', 'PS_IMPEDANCE_100MS':'Impedance_0.1s', 'PS_IMPEDANCE_1S':'Impedance_1s', 'PS_IMPEDANCE_5S':'Impedance_5s',
         'PS_IMPEDANCE_30S':'Impedance_30s', 'PS_IMPEDANCE_60S':'Impedance_60s', 'PS_REALDATE':'Realdate', 'PS_REALCLOCK':'Realtime', 'File_ID_cyc':'Cyc_ID', 'File_version_cyc':'Cyc_version', 'File_create_date_cyc':'Cyc_create_date', 'PS_TOT_TIME':'Total_time', 'cyc_file_path':'Cyc_file_path'}
        result = result.rename(columns = change_columns)
        return result

        
def DW_load(df, conn, db_name='ch-dch_database', table_name = 'integ_cyc'):
    # cur = con.cursor()
    # cur.execute(f'''
    #     CREATE TABLE IF NOT EXISTS {table_name}(
    #         Cyc_ID TEXT,
    #         Cyc_version TEXT,
    #         Cyc_create_date datetime,
    #         Total_time timestamp,
    #         Cyc_file_path TEXT,
    #         Channel_No TEXT,
    #         Channel_steptype TEXT,
    #         Current_cycle_number int,
    #         Total_cycle_number int,
    #         Setting_voltage float,
    #         Setting_current float,
    #         End_time timestamp,
    #         End_voltage float,
    #         End_current float,
    #         End_charge float,
    #         Test_name TEXT,
    #         Reseacher TEXT,
    #         Description_sch TEXT,
    #         Sequence int,
    #         Steptime timestamp,
    #         CV_end_time timestamp,
    #         TOT_TIME_CARRY float,
    #         Voltage float,
    #         Current float,
    #         Capacity float,
    #         Integral_capacity float,
    #         Charge_capacity float,
    #         Discharge_capacity float,
    #         Watt_hour float,
    #         Integral_watthour float,
    #         Charge_watthour float,
    #         Discharge_watthour float,
    #         Average_current float,
    #         Average_voltage float,
    #         Temperature float,
    #         Impedance float,
    #         Watt float,
    #         Capacity_sum float,
    #         Watthour_sum float,
    #         Chamber_temperature float,
    #         Temperature2 float,
    #         Charge_CC_capacity float,
    #         Charge_CV_capacity float,
    #         Discharge_CC_capacity float,
    #         Discharge_CV_capacity float,
    #         "Impedance_0.1s" float,
    #         Impedance_1s float,
    #         Impedance_5s float,
    #         Impedance_30s float,
    #         Impedance_60s float,
    #         Realdate datetime,
    #         Realtime timestamp
    #     )
    #     ''')
    
    df.to_sql(f'{table_name}', conn, if_exists='append', index = False)
        
if __name__ == '__main__':
    
    # find data
    root_path = r'/project/work/temp_venv/data/02_raw_data_charge/Overall_data'
    file_search = File_search(root_path)
    file_list = file_search.integration_list()
    
    conn = sqlite3.connect('/project/work/temp_venv/ch-dch_database.db')
    
    # 파일 리스트만큼 반복
    for file in tqdm(file_list, desc='DB 적재 진행중', unit='file'):
        try:
            cyc_cts_sch = cyc_cts_sch_comb(file['.cyc'], file['.cts'], file['.sch'])
            cyc_result, cts_result, sch_result = cyc_cts_sch.comb_data_preprocessing()
            DW_load(cyc_result, conn, db_name = 'ch-dch_database', table_name = 'sodium_cyc')
            DW_load(cts_result, conn, db_name = 'ch-dch_database', table_name = 'sodium_cts')
            DW_load(sch_result, conn, db_name = 'ch-dch_database', table_name = 'sodium_sch')
            print(f"[완료] {file['.cyc']}")
            print(f"[완료] {file['.cts']}")
            print(f"[완료] {file['.sch']}")
        except Exception as e:
            tqdm.write(f"[오류] {file['.cyc']} → {e}")
    
    conn.commit()
    conn.close()