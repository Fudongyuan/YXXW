from datetime import datetime

from flask import current_app

from . import passport_blueprint
from libs.captcha.captcha import captcha
from flask import make_response, request, jsonify, session
from info import redis_store, constants, db
from info.response_code import RET
import re
from info.models import User
import random
from info.utils.sms import send_sms


@passport_blueprint.route('/image_code')
def image_code():
    # 调用对象的方法
    text, code, image = captcha.generate_captcha()
    print(code)
    # 接收客户端的唯一值
    code_id = request.args.get('code_id')
    # 将数据保存到redis中，用于进行后续的验证
    redis_store.setex(code_id, constants.IMAGE_CODE_REDIS_EXPIRES, code)
    # 构造响应对象，将图片数据返回给浏览器
    response = make_response(image)
    # 设置响应报文的头，指定数据类型为图片
    response.headers['Content-Type'] = 'image/png'
    return response


@passport_blueprint.route('/smscode', methods=['POST'])
def smscode():
    '''生成短信验证码，并发送短信'''
    # 1.接收
    mobile = request.json.get('mobile')
    image_request = request.json.get('image_code')
    code_id = request.json.get('image_code_id')

    # 2.验证
    # 2.1非空
    if not all([mobile, image_request, code_id]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    # 2.2获取图形验证码
    image_redis = redis_store.get(code_id)
    if image_redis is None:
        return jsonify(errno=RET.NODATA, errmsg='图形验证码过期')
    # 2.3两个验证码是否一致
    # 注意：所有从redis中读取出来的数据，都是bytes类型
    if image_request != image_redis.decode():
        return jsonify(errno=RET.DATAERR, errmsg='图形验证码错误')
    # 2.4验证手机号格式
    if not re.match(r'^1[3-9]\d{9}$', mobile):
        return jsonify(errno=RET.DATAERR, errmsg='手机号错误')
    # 2.5手机号是否已经被注册
    mobile_count = User.query.filter_by(mobile=mobile).count()
    if mobile_count > 0:
        return jsonify(errno=RET.DATAEXIST, errmsg='手机号已经被注册')

    # 3.处理
    # 3.1随机生成6位值
    code = str(random.randint(100000, 999999))
    # 3.2保存到redis
    redis_store.setex(mobile, constants.SMS_CODE_REDIS_EXPIRES, code)
    # 3.3发送短信
    send_sms(mobile, [code, '5'], 1)
    print(code)

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@passport_blueprint.route('/register', methods=['POST'])
def register():
    '''注册：向用户表中添加一条数据'''
    # 1.接收
    mobile = request.json.get('mobile')
    sms_request = request.json.get('smscode')
    password = request.json.get('password')

    # 2.验证
    # 2.1非空
    if not all([mobile, sms_request, password]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')
    # 2.2获取短信验证码
    sms_redis = redis_store.get(mobile)
    if sms_redis is None:
        return jsonify(errno=RET.NODATA, errmsg='短信验证码过期')
    # 2.3手机验证码是否正确
    if sms_request != sms_redis.decode():
        return jsonify(errno=RET.DATAERR, errmsg='验证码错误')

    # 3.处理:向表中添加数据
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password
    # user.pasword(pwd)
    db.session.add(user)
    db.session.commit()

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@passport_blueprint.route('/login', methods=['POST'])
def login():
    '''从用户表中查询用户对象'''
    # 1.接收
    mobile = request.json.get('mobile')
    password = request.json.get('password')

    # 2.验证
    # 2.1非空
    if not all([mobile, password]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')

    # 3.处理：查询用户
    user = User.query.filter_by(mobile=mobile).first()
    # 判断手机号是否正确
    if user is None:
        return jsonify(errno=RET.DATAERR, errmsg='手机号错误')
    # 验证密码是否正确
    if not user.check_password(password):
        return jsonify(errno=RET.DATAERR, errmsg='密码错误')

    # 更新最近的登录时间
    user.update_time = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    # 用户登录成功
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name

    # 4.响应
    return jsonify(errno=RET.OK, errmsg='')


@passport_blueprint.route('/logout', methods=['POST'])
def logout():
    '''退出：删除session中的登录状态'''
    if 'user_id' in session:
        session.pop('user_id')
    if 'nick_name' in session:
        session.pop('nick_name')
    return jsonify(errno=RET.OK, errmsg='')
