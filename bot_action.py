import sqlite3

def query_for_top5(db_path, product_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows= c.execute("select brand_name,product_name, product_img, product_vol, \
    product_price from products where product_type=? and product_rank between 1 and 5", (str(product_type),))

    contents=rows.fetchall()
    c.close()

    return contents

def query_for_heavy_check(db_path, user_name):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows= c.execute("Select user_id, user_name From users Where user_name=?", (str(user_name),))

    contents=rows.fetchall()

    c.close()

    return contents

def get_user_id(db_path, user_name):
    conn=sqlite3.connect(db_path)
    c=conn.cursor()

    c.execute("SELECT user_id FROM USERS WHERE user_name=?",(str(user_name),))

    user_id=c.fetchone()
    user_id=user_id[0]

    return user_id

def query_for_teenage(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

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
                    LIMIT 5",(str(product_type), str(skin_type),))
    contents=rows.fetchall()
    
    c.close()

    return contents

def query_for_teenage_len3(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 10 and 19) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(product_type), str(skin_type),))
    contents=rows.fetchall()

    c.close()

    for row in contents:
        print(row)

    return contents

def query_for_early_tweenties(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

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
                LIMIT 5",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_early_tweenties_len3(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 20 and 24) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_late_tweenties(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

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
                LIMIT 5",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_late_tweenties_len3(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 25 and 29) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_early_thirties(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

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
                LIMIT 5",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_early_thirties_len3(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age between 30 and 34) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_late_thirties(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

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
                LIMIT 5",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def query_for_late_thirties_len3(db_path, product_type, skin_type):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rows = c.execute("Select u.user_id, p.product_id, AVG(r.rating), COUNT(r.rating)\
                            FROM ratings as r\
                            LEFT JOIN products AS p\
                            ON r.product_id=p.product_id\
                            LEFT JOIN users AS u\
                            ON  r.user_id=u.user_id\
                            WHERE (p.product_type=?) and (u.age >= 35) and (u.skin_type=?)\
                            GROUP BY p.product_id\
                            HAVING AVG(r.rating)>=4 and COUNT(r.rating)>=3\
                            LIMIT 3",(str(product_type), str(skin_type),))

    contents=rows.fetchall()

    c.close()

    return contents

def heavy_recomm(db_path, recomm):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(int(recomm[4]),int(recomm[3]),int(recomm[2]),int(recomm[1]),int(recomm[0]), ))

    rec_list=rec_list.fetchall()
    
    c.close()

    return rec_list


def filtering_rec_list_len3(db_path, content):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
                product_id=? or product_id=?",(int(content[0][1]),int(content[1][1]),int(content[2][1])))
    
    rec_list=rec_list.fetchall()
    
    c.close()

    return rec_list

def filtering_rec_list(db_path, content):
    conn=sqlite3.connect(db_path)

    c=conn.cursor()

    rec_list=c.execute("select brand_name, product_name, product_img, product_vol, product_price from products where product_id=? or \
            product_id=? or product_id=? or product_id=? or product_id=?",(int(content[0][1]),int(content[1][1]),
            int(content[2][1]),int(content[3][1]),int(content[4][1]), ))
    
    rec_list=rec_list.fetchall()

    c.close()

    return rec_list

