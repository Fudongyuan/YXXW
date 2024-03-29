from qiniu import Auth, put_data

# 需要填写你的 Access Key 和 Secret Key
access_key = 'DEA9zBeT4psDn54ej2DW0-JimW6ptFoF7-uhX6OY'
secret_key = 'd0pHyrAveyAr8ZIkDOCQWR0tOq3RPunUKbBP74my'
# 要上传的空间
bucket_name = 'ihome'


def storage(data):
    """七牛云存储上传文件接口"""
    if not data:
        return None
    # 构建鉴权对象
    q = Auth(access_key, secret_key)
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name)
    # 上传文件
    ret, info = put_data(token, None, data)
    if info and info.status_code != 200:
        raise Exception("上传文件到七牛失败")
    # 返回七牛中保存的图片名，这个图片名也是访问七牛获取图片的路径
    return ret["key"]
