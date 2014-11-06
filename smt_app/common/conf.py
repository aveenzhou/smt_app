#coding=utf-8
'''
Created on 2014-11-1

@author: aveenzhou
'''
from web.contrib.template import render_jinja

OPEN_API_URL="http://gw.api.alibaba.com/openapi"

AUTH_URL="http://gw.api.alibaba.com/auth/authorize.htm"

APP_KEY="1067520"
APP_SECRET="PUpMcxJ5om"

TOKEN_URL="https://gw.api.alibaba.com/openapi/http/1/system.oauth2/getToken/"+APP_KEY
LOCAL_APP_URL="http://127.0.0.1:8080/auth"

###################
MONGODB={
#            "DB_SERVER":'10.20.14.196',
            "DB_SERVER":'192.168.1.103',
#            "DB_SERVER":'localhost',

#            "DB_PORT":28888,
            "DB_PORT":27017,
            "DB_NAME":'smt_app_db',
            "DB_SMT_COLL":'smt_procucts_coll',
            "DB_TOKEN_COLL":'smt_token_coll',
            "DB_USER":'aveen',
            "DB_ADMIN_PWD":'123456',
            "DB_PWD":'123',
            "IS_AUTH":False
         }
##########################

USER={
      'admin':{'password':'admin1989','role':1},
      'visitor':{'password':'123456','role':0}
      }




