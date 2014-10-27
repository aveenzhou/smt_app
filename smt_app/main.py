#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''

import urllib3
import json
import hashlib
import hmac
import web
import urllib

AUTH_URL="http://gw.api.alibaba.com/auth/authorize.htm"

APP_KEY="1067520"
APP_SECRET="PUpMcxJ5om"

TOKEN_URL="https://gw.api.alibaba.com/openapi/http/1/system.oauth2/getToken/"+APP_KEY
LOCAL_APP_URL="http://127.0.0.1:8080/index"

def get_alibba_auth_url():
    auth_args={
               "client_id":APP_KEY,
               "site":"aliexpress",
               "redirect_uri":LOCAL_APP_URL,
               "state":'test'
               }
    
    def create_sign_str(args):
        keys=args.keys()
        sorted_keys=sorted(keys)
        temp=[]
        for key in sorted_keys:
            temp.append(''.join((key,auth_args[key])))
        
        sign_str=''.join(temp)
        encry_sign_str=hmac.new(APP_SECRET, sign_str, digestmod=hashlib.sha1).hexdigest().upper() #hmac_sha1加密算法
        return encry_sign_str
    auth_args['_aop_signature']=create_sign_str(auth_args)
    
    url= '?'.join((AUTH_URL,urllib.urlencode(auth_args)))
    return url

def get_token_by_code(code):
    req_args={
              "grant_type":"authorization_code",
              "need_refresh_token":"true"
              }
    

web.config.alibba_auth_url=get_alibba_auth_url()


########################################
urls=(
      '/auth','Auth',
      '/index','Index'
      )

class Auth(object):
    def GET(self):
        redirect_url=web.config.alibba_auth_url
        web.seeother(redirect_url, absolute=True)
    

class Index(object):
    def GET(self):
        input= web.input()
        code=input.get('code','') #临时授权码
        if not code:
            web.seeother('/auth')
        return  code
        



app = web.application(urls, globals())
application=app.wsgifunc()

if __name__=="__main__":
    app.run()

    
    
    
    