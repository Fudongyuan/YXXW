from libs.ytx_sdk.CCPRestSDK import REST
from info import constants


def send_sms(mobile, data, tempId):
    rest = REST(constants.SERVERIP, constants.SERVERPORT, constants.SOFTVERSION)
    rest.setAccount(constants.ACCOUNTSID, constants.ACCOUNTTOKEN)
    rest.setAppId(constants.APPID)
    result = rest.sendTemplateSMS(mobile, data, tempId)
