from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from info import constants
from info import db


class BaseModel(object):
    """模型基类，为每个模型补充创建时间与更新时间"""
    create_time = db.Column(db.DateTime, default=datetime.now)  # 记录的创建时间
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


# 用户收藏表，建立用户与其收藏新闻多对多的关系
tb_user_news_collection = db.Table(
    "info_user_news_collection",
    db.Column("user_id", db.Integer, db.ForeignKey("info_user.id"), primary_key=True),  # 新闻编号
    db.Column("news_id", db.Integer, db.ForeignKey("info_news.id"), primary_key=True),  # 分类编号
    db.Column("create_time", db.DateTime, default=datetime.now)  # 收藏创建时间
)

tb_user_author = db.Table(
    "info_user_author",
    db.Column('user_id', db.Integer, db.ForeignKey('info_user.id'), primary_key=True),  # 浏览者编号
    db.Column('author_id', db.Integer, db.ForeignKey('info_user.id'), primary_key=True)  # 作者编号
)


class User(BaseModel, db.Model):
    """用户"""
    __tablename__ = "info_user"

    id = db.Column(db.Integer, primary_key=True)  # 用户编号
    nick_name = db.Column(db.String(32), unique=True, nullable=False)  # 用户昵称
    password_hash = db.Column(db.String(128), nullable=False)  # 加密的密码
    mobile = db.Column(db.String(11), unique=True, nullable=False)  # 手机号
    avatar_url = db.Column(db.String(256),default='user_pic.png')  # 用户头像路径
    last_login = db.Column(db.DateTime, default=datetime.now)  # 最后一次登录时间
    is_admin = db.Column(db.Boolean, default=False)
    signature = db.Column(db.String(512))  # 用户签名
    gender = db.Column(  # 性别的状态
        db.Enum(
            "MAN",  # 男
            "WOMAN"  # 女
        ),
        default="MAN")

    # 当前用户收藏的所有新闻：维护的是User和News的多对多的关系
    collection_news = db.relationship("News", secondary=tb_user_news_collection, lazy="dynamic")  # 用户收藏的新闻
    authors = db.relationship(
        'User',
        lazy='dynamic',
        secondary=tb_user_author,
        backref=db.backref('users', lazy='dynamic'),
        #当前对象调用authors属性时，使用primaryjoin条件
        primaryjoin=id == tb_user_author.c.user_id,
        #当前对象调用backref属性即users时，使用secondaryjoin条件
        secondaryjoin=id == tb_user_author.c.author_id
    )

    # 当前用户所发布的新闻：relationship维护的是User和News的一对多的关系
    # backref:维护的是多对一
    news_list = db.relationship('News', backref='user', lazy='dynamic')

    @property
    def password(self):
        """
        这个方法时password属性的getter方法
        :return: 我的思想是：不让通过这个属性读取密码，所以抛异常
        """
        raise AttributeError('can not read')

    @password.setter
    def password(self, value):
        """
        这个方法时password属性的setter方法
        :param value: 外界传入的明文密码
        :return: 密文密码
        """
        self.password_hash = generate_password_hash(value)
    #对象.password(参数)===>对象.password=参数
    # def set_passwordhash_with_password(self, password):
    #     from werkzeug.security import generate_password_hash, check_password_hash
    #     self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        校验密码
        :param password: 外界传入的密码明文
        :return: 如果校验通过，返回True。反之，返回False
        """
        return check_password_hash(self.password_hash, password)

    def to_login_dict(self):
        return {
            'id':self.id,
            'nick_name':self.nick_name,
            # 'avatar_url':'/static/news/images/'+self.avatar_url
            'avatar_url':constants.QINIU_DOMIN_PREFIX+self.avatar_url
        }
    def to_dict(self):
        return {
            'id':self.id,
            'nick_name':self.nick_name,
            'signature':self.signature if self.signature else '',
            'gender':self.gender,
            'total_news':self.news_list.count(),
            'total_fans':self.users.count(),
            'avatar_url':constants.QINIU_DOMIN_PREFIX+self.avatar_url
        }
    def to_admin_dict(self):
        return {
            'id':self.id,
            'nick_name':self.nick_name,
            'create_time':self.create_time,
            'update_time':self.update_time,
            'mobile':self.mobile
        }


class News(BaseModel, db.Model):
    """新闻"""
    __tablename__ = "info_news"

    id = db.Column(db.Integer, primary_key=True)  # 新闻编号
    title = db.Column(db.String(256), nullable=False)  # 新闻标题
    source = db.Column(db.String(64), nullable=False)  # 新闻来源
    digest = db.Column(db.String(512), nullable=False)  # 新闻摘要
    content = db.Column(db.Text, nullable=False)  # 新闻内容
    clicks = db.Column(db.Integer, default=0)  # 浏览量
    index_image_url = db.Column(db.String(256))  # 新闻列表图片路径
    category_id = db.Column(db.Integer, db.ForeignKey("info_category.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("info_user.id"))  # 当前新闻的作者id
    status = db.Column(db.Integer, default=1)  # 当前新闻状态 如果为0代表审核通过，1代表审核中，-1代表审核不通过
    reason = db.Column(db.String(256))  # 未通过原因，status = -1 的时候使用
    # 当前新闻的所有评论
    comments = db.relationship("Comment", lazy="dynamic")

    def to_click_dict(self):
        return {
            'id':self.id,
            'title':self.title
        }
    def to_index_dict(self):
        '''
        {
                'id':**,
                'title':**,
                'digest':**,
                'source':**,
                'create_time':**,
            }
        '''
        return {
            'id':self.id,
            'title':self.title,
            'digest':self.digest,
            'source':self.source,
            'create_time':self.create_time,
            # 'index_image_url':'/static/news/images/'+self.index_image_url,
            'index_image_url':constants.QINIU_DOMIN_PREFIX+str(self.index_image_url),
            'content':self.content,
            'category':self.category.name,
            'category_id':self.category_id
        }
    def to_release_dict(self):
        return {
            'id':self.id,
            'title':self.title,
            'status':self.status,
            'reason':self.reason,
            'create_time':self.create_time
        }


class Category(BaseModel, db.Model):
    """新闻分类"""
    __tablename__ = "info_category"

    id = db.Column(db.Integer, primary_key=True)  # 分类编号
    name = db.Column(db.String(64), nullable=False)  # 分类名
    news_list = db.relationship('News', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id':self.id,
            'name':self.name
        }


class Comment(BaseModel, db.Model):
    """评论"""
    __tablename__ = "info_comment"

    id = db.Column(db.Integer, primary_key=True)  # 评论编号
    user_id = db.Column(db.Integer, db.ForeignKey("info_user.id"), nullable=False)  # 用户id
    news_id = db.Column(db.Integer, db.ForeignKey("info_news.id"), nullable=False)  # 新闻id
    content = db.Column(db.Text, nullable=False)  # 评论内容
    comment_id = db.Column(db.Integer, db.ForeignKey("info_comment.id"))  # 父评论id
    back_list=db.relationship('Comment',lazy='dynamic')#,backref='comment'
    like_count = db.Column(db.Integer, default=0)  # 点赞条数

    def to_dict(self):
        return {
            'id':self.id,
            'user':User.query.get(self.user_id).to_login_dict(),
            'content':self.content,
            'create_time':self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'like_count':self.like_count,
            'backs':[back.to_back_dict() for back in self.back_list.order_by(Comment.id.desc())],
            'like':False
        }
    def to_back_dict(self):
        return {
            'id':self.id,
            'nick_name':User.query.get(self.user_id).nick_name,
            'content':self.content
        }


class CommentLike(BaseModel, db.Model):
    """评论点赞"""
    __tablename__ = "info_comment_like"
    comment_id = db.Column("comment_id", db.Integer, db.ForeignKey("info_comment.id"), primary_key=True)  # 评论编号
    user_id = db.Column("user_id", db.Integer, db.ForeignKey("info_user.id"), primary_key=True)  # 用户编号
