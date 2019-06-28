from info.models import News
from info import constants

def get_click_list():
    news_list1 = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    # 2.将每个新闻对象转成字典，构造新列表====>列表推导式,[dict,dict,dict,...]
    news_list2 = [news.to_click_dict() for news in news_list1]

    return news_list2
