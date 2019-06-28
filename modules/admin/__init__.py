from flask import Blueprint,session,redirect,request,g
from info.models import User

admin_blueprint=Blueprint('admin',__name__,url_prefix='/admin')
from . import views

# @app.before_request==============>在所有视图函数中有效
@admin_blueprint.before_request#===>只在当前蓝图注册的视图函数中有效
def login_valid():
    #当请求登录视图，不需要进行验证
    #注册请求勾子函数后，所有的视图都会执行这个函数
    #但是对于极少数视图，是不希望执行，则进行判断实现排除
    ignore_list=['/admin/login']
    if request.path not in ignore_list:
        if 'admin_user_id' not in session:
            return redirect('/admin/login')
        else:
            g.user=User.query.get(session['admin_user_id'])

