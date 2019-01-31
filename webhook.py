import telebot
from telebot import types
from aiohttp import web
import ssl
import logging
import sqlite3
import lightfm
import pickle
from recsys import *
import time
import pandas as pd

#webhook 설정에 필요한 정보들
WEBHOOK_LISTEN = ""
WEBHOOK_PORT = 

WEBHOOK_SSL_CERT = ""
WEBHOOK_SSL_PRIV = ""

API_TOKEN = ""
bot = telebot.TeleBot(API_TOKEN)

#app 생성
app = web.Application()

#자주 쓰이는 챗봇 키보드 레이아웃을 미리 만들어 놓는다.
reply_keyboard = [['스킨', '로션', '에센스'],
                  ['10대', '20대 초반', '20대 후반', '30대 초반', '30대 후반 이상'],
                  ['건성', '지성', '중성', '복합성', '민감성']
                  ]

#도움말 챗 스크립트(/help)
help_string = []
help_string.append("*Commelier M.L* - Bonjour~! 안녕하세요!\n")
help_string.append("화장품 추천 챗봇 *Commelier M.L* 입니다 @>~~\n\n")
help_string.append("/start - 챗봇 도움말 보기\n")
help_string.append("/top5 - 탑5 화장품 추천\n")
help_string.append("/recomm - 기존 유저 추천 받기\n")
help_string.append("/new - 신규 유저 추천 받기")


#유저 정보를 담아둘 변수를 생성
user_dict={}

#유저 클래스
class User:
    def __init__(self):
        """
        유저의 이름, 피부타입, 나이, 추천 받고 싶어하는 제품 종류를 설정한다.
        """
        self.name=None
        self.skin_type=None
        self.age=None
        #self.gender=None 여자의 수가 압도적으로 많아서 나중에 데이터를 더 모으면 쓰도록한다.
        self.product_type=None

# 연결 부분?
async def handle(request):
    if request.match_info.get("token") == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)

app.router.add_post("/{token}/", handle)


#챗봇 기능

#입장시 인사 및 도움말을 제공하는 기능
@bot.message_handler(commands=["start"])
def send_help(message):
    bot.send_message(message.chat.id, "".join(help_string), parse_mode="Markdown")

#선택한 제품을 랭킹에서 상위5개 추천하는 기능
#빠른 추천을 원하는 유저들에게 편의를 제공한다.
#키보드 마크업을 통해 유저와 상호작용이 가능하다. 
@bot.message_handler(commands=["top5"])
def send_top_5(message):
    try:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[0][0], reply_keyboard[0][1], reply_keyboard[0][2])

        msg=bot.reply_to(message, "어떤 제품을 추천 받고 싶나요?", reply_markup=markup)
        
        #추천 받고 싶은 제품 종류를 선택하고 정보를 다음 함수로 넘겨준다.
        bot.register_next_step_handler(msg, process_top_step)
    except Exception as e:
        bot.reply_to(message, "뭔가 잘못된거 같아요")

#유저가 원하는 제품 정보를 받아서 DB에서 검색 후 결과를 전송한다.
#이 때 한 개의 메세지에 한 개 제품이 들어가고 이미지를 누르면 제품 이미지를 볼 수 있고
#텍스트를 누르면 해당 제품 검색 페이지로 넘어간다.
def process_top_step(message):
    chat_id = message.chat.id
    product_type = (str(message.text),)

    conn=sqlite3.connect("./glow_db.sqlite3")

    c=conn.cursor()

    rows= c.execute("select brand_name,product_name, product_img, product_vol, \
    product_price from products where product_type=? and product_rank between 1 and 5",product_type)

    content=rows.fetchall()
    conn.close()


    #순차적으로 추천 제품을 메세지로 보낸다.
    for row in range(len(content)):
        msg_upper=content[row][0]+"\n"+content[row][1]
        msg_lower=content[row][3]+" / "+content[row][4]
        
        #bot.send_message(chat_id, msg_upper)
        bot.send_photo(chat_id, photo=content[row][2], \
        caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+content[row][1].replace(" ","")+")",\
        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

#글로우 픽의 랭킹에 등록되어있는 제품에 리뷰를 남긴 사용자(헤비 유저)에게 리뷰 정보를 기반으로 추천을 해주는 기능
#기본 알고리즘으로 빠르고 가벼운 lightFM을 사용하였다. 이후 해야할 일은 제품별 알고리즘을 만들고 저장하고 로드하는
#방식으로 바꾸는 일이다.
@bot.message_handler(commands=["recomm"])
# 해당 핸들러의 흐름은 다음과 같다.
# 1. 원하는 제품 종류 입력
# 2. 유저의 닉네임을 입력 받은 후 해당 닉네임으로 리뷰가 존재하면 lightFM 작동, 없다면 추천 방식을 물어본다.
# 3-1. lightFM 작동의 경우, DB쿼리를 통해 원하는 정보를 추출하고 알고리즘에 맞는 형태의 데이터로 전처리하고
# 알고리즘을 작동시킨다.
# 3-2. 추천 방식을 물어본다. 추천 방식에는 베스트 랭킹, 신규 유저, 필요없음 이 있다.


def check_product_type(message):
    try:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[0][0], reply_keyboard[0][1], reply_keyboard[0][2])

        msg=bot.reply_to(message, "어떤 제품을 추천 받고 싶나요?", reply_markup=markup)
            
        bot.register_next_step_handler(msg, check_name_recomm)

    except Exception as e:
        bot.reply_to(message, "뭔가 잘못된거 같아요")

def check_name_recomm(message):
    user = User()
    
    chat_id = message.chat.id
    product_type = message.text

    user.product_type = product_type

    user_dict[chat_id]=user

    msg=bot.reply_to(message, "글로우픽 닉네임을 입력해주세요.", reply_markup=types.ForceReply())
    bot.register_next_step_handler(msg, check_recomm_method_step)

#헤비 유저를 위한 추천 모델 알고리즘
def check_recomm_method_step(message):
    chat_id=message.chat.id
    name=message.text

    user=user_dict[chat_id]
    user.name=name

    conn=sqlite3.connect("./glow_db.sqlite3")

    c=conn.cursor()

    rows= c.execute("select * from reviews left join products on reviews.product_id=products.product_id\
    where products.product_type=? and reviews.user_name=?" ,(user.product_type, user.name))

    content=rows.fetchall()

    if len(content)==0:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row("베스트 랭킹", "신규 추천", "필요없어")
        msg=bot.reply_to(message, "해당 아이디는 리뷰를 남긴 적이 없어요ㅜㅜ.\n대신에 베스트 화장품이나 신규 추천을 해드릴까요?", reply_markup=markup)

        bot.register_next_step_handler(msg, check_which_way)
    else:
        
        try:
            ratings=c.execute("select * from ratings where product_id in (select product_id from products where product_type=?)",(user.product_type,))
            ratings=ratings.fetchall()
            ratings=pd.DataFrame(columns=["user_id", "product_id", "rating"] ,data=ratings).copy()

            products= c.execute("select product_id, brand_name, product_name, product_img, product_vol, product_price from products where product_type=?",(user.product_type,))
            products=products.fetchall()
            products=pd.DataFrame(columns=["product_id", "brand_name", "product_name", "product_img", "product_vol", \
                "product_price"], data=products).copy()

            user_id=c.execute("select user_id from users where user_name=?",(user.name,))
            user_id=user_id.fetchone()
            user_id=user_id[0]

            # Creating interaction matrix using rating data
            interactions = create_interaction_matrix(df = ratings,
                                                    user_col = 'user_id',\
                                                    item_col = 'product_id',\
                                                    rating_col = 'rating')

            # Create User Dict
            user_info = create_user_dict(interactions=interactions)
            # Create Item dict
            product_info = create_item_dict(df = products,\
                                        id_col = 'product_id',\
                                        name_col = 'product_name')

            mf_model = runMF(interactions = interactions)

            ## Calling 10 movie recommendation for user id 11
            rec_list = sample_recommendation_user(model = mf_model, \
                                                interactions = interactions, \
                                                user_id = user_id, \
                                                user_dict = user_info,\
                                                item_dict = product_info, \
                                                threshold = 4,\
                                                nrec_items = 5,\
                                                show = False)
            recomm=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(rec_list[0],rec_list[1],rec_list[2],rec_list[3],rec_list[4]))

            recomms=recomm.fetchall()
            conn.close()
            for row in range(len(recomms)):
                msg_upper=recomms[row][0]+"\n"+recomms[row][1]
                msg_lower=recomms[row][3]+" / "+recomms[row][4]
                
                #bot.send_message(chat_id, msg_upper)
                bot.send_photo(chat_id, photo=recomms[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+recomms[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

        except Exception as e:
            bot.reply_to(message, "뭔가 잘못된거 같아요")

#lightFM을 사용할 수 없는 경우 유저에게 대안을 제시하는 기능
def check_which_way(message):
    #탑5와 같은 기능
    if message.text=="베스트 랭킹":
        chat_id = message.chat.id
        user=user_dict[chat_id]
        product_type = (str(user.product_type),)

        conn=sqlite3.connect("./glow_db.sqlite3")

        c=conn.cursor()

        rows= c.execute("select brand_name,product_name, product_img, product_vol, \
        product_price from products where product_type=? and product_rank between 1 and 5",product_type)

        content=rows.fetchall()
        conn.close()
        for row in range(len(content)):
            msg_upper=content[row][0]+"\n"+content[row][1]
            msg_lower=content[row][3]+" / "+content[row][4]
            
            #bot.send_message(chat_id, msg_upper)
            bot.send_photo(chat_id, photo=content[row][2], \
            caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+content[row][1].replace(" ","")+")",\
            parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    
    #신규 유저에게 추천하는 필터링 방식의 추천 기능이다.
    #제품 종류, 나이, 피부 타입에 따라 필터링 후 평점과 리뷰 수를 기준으로 추천해준다.
    elif message.text=="신규 추천":
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[1][0], reply_keyboard[1][1], reply_keyboard[1][2])
        markup.row(reply_keyboard[1][3], reply_keyboard[1][4])
        msg = bot.reply_to(message, '실례지만 연령대가 어떻게 되세요?', reply_markup=markup)
        bot.register_next_step_handler(msg, process_no_age_step)

    #추천 과정을 종료한다. 
    elif message.text=="필요없어":
        bot.reply_to(message, "다음에 또 들러주세용 ^^", reply_markup=types.ReplyKeyboardRemove())

#신규 유저 추천을 누른 유저에게 나이대를 물어본다.
def process_no_age_step(message):
    try:
        chat_id = message.chat.id
        age = message.text
        user = user_dict[chat_id]

        if (age == u'10대') or (age == u'20대 초반') or (age == u'20대 후반') or (age == u'30대 초반')\
         or (age == u'30대 후반 이상'):
            user.age = age
        else:
            raise Exception()

        #피부 타입과 관련된 정보를 얻기 위해 키보드 마크업을 보여주고 유저와 상호작용 한다.
        #이후 스킨 타입을 입력 받기위해 해당 함수로 넘어간다.
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[2][0], reply_keyboard[2][1], reply_keyboard[2][2])
        markup.row(reply_keyboard[2][3], reply_keyboard[2][4])
        msg = bot.reply_to(message, '피부 타입은 어떻게 되세요?', reply_markup=markup)
        bot.register_next_step_handler(msg, process_no_skin_type_step)
    except Exception as e:
        bot.reply_to(message, '뭔가 잘못된거 같아요ㅠㅠ')

#피부 타입 정보를 입력받고 나이대와 피부 타입에 따라 필터링을 실시하고 화장품을 추천해준다.
def process_no_skin_type_step(message):
    try:
        chat_id = message.chat.id
        skin_type = message.text
        user = user_dict[chat_id]

        if (skin_type == u'건성') or (skin_type == u'지성') or (skin_type == u'복합성') or (skin_type == u'중성')\
         or (skin_type == u'민감성'):
            user.skin_type = skin_type
        else:
            raise Exception()
        bot.reply_to(message, '추천 화장품을 고르는 중입니다.\n잠시만 기다려 주세요.', reply_markup=types.ReplyKeyboardRemove())
        
        #나이, 스킨 타입, 제품 종류를 필터링한다.
        if user.age=="10대":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()
            
            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 10 and 19) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(str(user.product_type), str(user.skin_type),))
            content = rows.fetchall()

            #현재로써는 데이터가 부족하여 필터링 후 5개 추천 항목이 나오지 않으면 필터링 조건을 완화하여 3가지 제품을 추천한다.
            if len(content)<5:
                rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 10 and 19) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(user.product_type), str(user.skin_type),))
                content=rows.fetchall()
                
                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1]))

                rec_list=rec_list.fetchall()

                #추천 결과 전송
                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
            
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()
        
        if user.age=="20대 초반":
            conn=sqlite3.connect("./glow_db.sqlite3")
            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                        FROM ratings as r\
                        LEFT JOIN products AS p\
                        ON r.product_id=p.product_id\
                        LEFT JOIN users AS u\
                        ON  r.user_id=u.user_id\
                        WHERE (p.product_type=?) and (u.age between 20 and 24) and (u.skin_type=?)\
                        GROUP BY p.product_id\
                        HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                        LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 20 and 24) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))
                
                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))

            rec_list=rec_list.fetchall()
                
            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()

        if user.age=="20대 후반":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 25 and 29) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 25 and 29) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
            
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()

        if user.age=="30대 초반":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 30 and 34) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 30 and 34) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
                
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]            
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            c.close()

        if user.age=="30대 후반 이상":
                conn=sqlite3.connect("./glow_db.sqlite3")

                c=conn.cursor()

                rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                                FROM ratings as r\
                                LEFT JOIN products AS p\
                                ON r.product_id=p.product_id\
                                LEFT JOIN users AS u\
                                ON  r.user_id=u.user_id\
                                WHERE (p.product_type=?) and (u.age >= 35) and (u.skin_type=?)\
                                GROUP BY p.product_id\
                                HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                                LIMIT 5",(user.product_type, user.skin_type))
                content = rows.fetchall()

                if len(content)<5:
                    rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                                FROM ratings as r\
                                LEFT JOIN products AS p\
                                ON r.product_id=p.product_id\
                                LEFT JOIN users AS u\
                                ON  r.user_id=u.user_id\
                                WHERE (p.product_type=?) and (u.age >= 35) and (u.skin_type=?)\
                                GROUP BY p.product_id\
                                HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                                LIMIT 3",(user.product_type, user.skin_type))
                    content=rows.fetchall()

                    rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                    product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                    rec_list=rec_list.fetchall()

                    for row in range(len(rec_list)):
                        msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                        msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                        
                        
                        bot.send_photo(chat_id, photo=rec_list[row][2], \
                        caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                
                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
                
                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

                c.close()

        time.sleep(3)
        bot.send_message(message.chat.id, "감사합니다.^^")
    except Exception as e:
        bot.reply_to(message, '뭔가 잘못된거 같아요ㅠㅠ')



#신규 유저에게 필터링을 통한 추천 서비스를 제공한다. 위에서 제공한 필터링과 동일한 기능
@bot.message_handler(commands=["new"])
def process_name_step(message):
    try:
        chat_id=message.chat.id
        #name=message.text
        user=User()
        #user.name=name
        user_dict[chat_id]=user

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[0][0], reply_keyboard[0][1], reply_keyboard[0][2])

        msg=bot.reply_to(message, "어떤 제품을 추천 받고 싶나요?", reply_markup=markup)
        
        bot.register_next_step_handler(msg, process_product_step)
    except Exception as e:
        bot.reply_to(message, "뭔가 잘못된거 같아요")

def process_product_step(message):
    try:
        chat_id = message.chat.id
        product_type = message.text
        user = user_dict[chat_id]
        user.product_type = product_type

        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[1][0], reply_keyboard[1][1], reply_keyboard[1][2])
        markup.row(reply_keyboard[1][3], reply_keyboard[1][4])
        msg = bot.reply_to(message, '실례지만 연령대가 어떻게 되세요?', reply_markup=markup)
        bot.register_next_step_handler(msg, process_age_step)
    except Exception as e:
        bot.reply_to(message, '뭔가 잘못된거 같아요 ㅜㅜ')

def process_age_step(message):
    try:
        chat_id = message.chat.id
        age = message.text
        user = user_dict[chat_id]

        if (age == u'10대') or (age == u'20대 초반') or (age == u'20대 후반') or (age == u'30대 초반')\
         or (age == u'30대 후반 이상'):
            user.age = age
        else:
            raise Exception()
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.row(reply_keyboard[2][0], reply_keyboard[2][1], reply_keyboard[2][2])
        markup.row(reply_keyboard[2][3], reply_keyboard[2][4])
        msg = bot.reply_to(message, '피부 타입은 어떻게 되세요?', reply_markup=markup)
        bot.register_next_step_handler(msg, process_skin_type_step)
    except Exception as e:
        bot.reply_to(message, '뭔가 잘못된거 같아요ㅠㅠ')


def process_skin_type_step(message):
    try:
        chat_id = message.chat.id
        skin_type = message.text
        user = user_dict[chat_id]

        if (skin_type == u'건성') or (skin_type == u'지성') or (skin_type == u'복합성') or (skin_type == u'중성')\
         or (skin_type == u'민감성'):
            user.skin_type = skin_type
        else:
            raise Exception()
       
        if user.age=="10대":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()
            
            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 10 and 19) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(str(user.product_type), str(user.skin_type),))
            content = rows.fetchall()

            if len(content)<5:
                rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 10 and 19) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(user.product_type), str(user.skin_type),))
                content=rows.fetchall()
                
                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1]))

                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                
                c.close()

                return
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
            
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()
        
        if user.age=="20대 초반":
            conn=sqlite3.connect("./glow_db.sqlite3")
            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                        FROM ratings as r\
                        LEFT JOIN products AS p\
                        ON r.product_id=p.product_id\
                        LEFT JOIN users AS u\
                        ON  r.user_id=u.user_id\
                        WHERE (p.product_type=?) and (u.age between 20 and 24) and (u.skin_type=?)\
                        GROUP BY p.product_id\
                        HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                        LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 20 and 24) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))
                
                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                
                c.close()

                return
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))

            rec_list=rec_list.fetchall()
                
            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()

        if user.age=="20대 후반":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 25 and 29) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 25 and 29) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                
                c.close()

                return
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
            
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]
                
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            c.close()

        if user.age=="30대 초반":
            conn=sqlite3.connect("./glow_db.sqlite3")

            c=conn.cursor()

            rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 30 and 34) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                            LIMIT 5",(user.product_type, user.skin_type))
            content = rows.fetchall()

            if len(content)<5:
                rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 30 and 34) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(user.product_type, user.skin_type))
                content=rows.fetchall()

                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                
                c.close()

                return
            
            rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
                
            rec_list=rec_list.fetchall()

            for row in range(len(rec_list)):
                msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                msg_lower=rec_list[row][3]+" / "+rec_list[row][4]            
                
                bot.send_photo(chat_id, photo=rec_list[row][2], \
                caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
            
            c.close()

        if user.age=="30대 후반 이상":
                conn=sqlite3.connect("./glow_db.sqlite3")

                c=conn.cursor()

                rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                                FROM ratings as r\
                                LEFT JOIN products AS p\
                                ON r.product_id=p.product_id\
                                LEFT JOIN users AS u\
                                ON  r.user_id=u.user_id\
                                WHERE (p.product_type=?) and (u.age >= 35) and (u.skin_type=?)\
                                GROUP BY p.product_id\
                                HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=10\
                                LIMIT 5",(user.product_type, user.skin_type))
                content = rows.fetchall()

                if len(content)<5:
                    rows= c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                                FROM ratings as r\
                                LEFT JOIN products AS p\
                                ON r.product_id=p.product_id\
                                LEFT JOIN users AS u\
                                ON  r.user_id=u.user_id\
                                WHERE (p.product_type=?) and (u.age >= 35) and (u.skin_type=?)\
                                GROUP BY p.product_id\
                                HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                                LIMIT 3",(user.product_type, user.skin_type))
                    content=rows.fetchall()

                    rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                    product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],))

                    rec_list=rec_list.fetchall()

                    for row in range(len(rec_list)):
                        msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                        msg_lower=rec_list[row][3]+" / "+rec_list[row][4]                        
                        
                        bot.send_photo(chat_id, photo=rec_list[row][2], \
                        caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
                    
                    c.close()

                    return
                
                rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=? or product_id=? or product_id=?",(content[0][1],content[1][1],content[2][1],content[3][1],content[4][1]))
                
                rec_list=rec_list.fetchall()

                for row in range(len(rec_list)):
                    msg_upper=rec_list[row][0]+"\n"+rec_list[row][1]
                    msg_lower=rec_list[row][3]+" / "+rec_list[row][4]                    
                    
                    bot.send_photo(chat_id, photo=rec_list[row][2], \
                    caption="["+msg_upper+'\n'+msg_lower+"](https://www.glowpick.com/search/result?query="+rec_list[row][1].replace(" ","")+")",\
                    parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

                c.close() 

    except Exception as e:
        bot.reply_to(message, '뭔가 잘못된거 같아요ㅠㅠ')

#아무거나 입력할 때 안내를 도와준다.
@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    # this is the standard reply to a normal message
    bot.send_message(m.chat.id, "죄송합니다. 무슨 말씀인지 잘 모르겠습니다.\n /start 를 통해 기능을 살펴볼 수 있습니다. ^^") 

# - - -

#ssl과 관련된 정보를 담고 있다.
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

# aiohttp 서버를 실행시킨다. 
web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
    ssl_context=context,
)
