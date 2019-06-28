import functools
from flask import session,g,redirect,request
from info.models import User

def login_wraps(view):
    @functools.wraps(view)
    def fun3(*args,**kwargs):
        #....
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
            #如果当前是用户中心，则转到首页
            if request.path.startswith('/profile'):
                return redirect('/')
        else:
            g.user = User.query.get(user_id)


        response=view(*args,**kwargs)

        #....

        return response


    return fun3
