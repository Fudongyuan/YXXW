from flask import render_template, session, request, jsonify, g
from info.models import User, News, Category
from . import index_blueprint
from info import constants
from info.response_code import RET
from info.utils.commons import get_click_list
from info.utils.wraps import login_wraps


@index_blueprint.route('/')
@login_wraps
def index():
    '''查询数据并显示'''
    # 用户登录状态
    # user_id = session.get('user_id')
    # if user_id is None:
    #     user = None
    # else:
    #     user = User.query.get(user_id).to_login_dict()

    # 分类信息[category,....]==>[dict,dict,...]
    # 1.查询所有分类
    category_list1 = Category.query.all()
    # 2.转字典
    category_list2 = [category.to_dict() for category in category_list1]

    # 点击量排行[news,news,....]
    # 1.根据点击量排序，取前n条新闻
    # news_list2=[]
    # for news in news_list1:
    #     news_list2.append(news.to_click_dict())
    news_list2 = get_click_list()

    # 新闻列表
    # if g.user:
    #     user_dict=g.user.to_login_dict()
    # else:
    #     user_dict=None
    user_dict = g.user.to_login_dict() if g.user else None
    data = {
        'user': user_dict,
        'news_list': news_list2,
        'category_list': category_list2
    }

    return render_template('news/index.html', data=data)


@index_blueprint.route('/newslist')
def newslist():
    # 1.接收：分类编号，页码，页大小
    page = request.args.get('page')
    cid = request.args.get('cid')
    per_page = request.args.get('per_page')

    # 2.验证
    if not all([page, cid, per_page]):
        return jsonify(errno=RET.NODATA, errmsg='数据不完整')

    # 3.处理：查询，过滤，分页
    pagination = News.query  # select * from ...
    # 如果分类编号大于0,表示指定某个分类，则拼接filter_by()语句
    if int(cid) > 0:
        pagination = pagination.filter_by(category_id=cid)  # where ...
    # order by ...
    pagination = pagination.order_by(News.id.desc()). \
        paginate(int(page), int(per_page), False)  # limit
    # 当前页数据
    news_list1 = pagination.items
    # 总页数
    total_page = pagination.pages
    # 4.响应
    news_list2 = [news.to_index_dict() for news in news_list1]

    '''
    {
            'totalPage':****,
            'newsList':[{
                'id':**,
                'title':**,
                'digest':**,
                'source':**,
                'create_time':**,
            },{},...]
        }
    '''
    data = {
        'totalPage': total_page,
        'newsList': news_list2
    }
    return jsonify(data)
