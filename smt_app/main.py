#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''
import os
import urllib3
import json
import hashlib
import hmac
import web
import urllib
import urllib2
import pymongo
from gevent.pywsgi import WSGIServer
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
#            "DB_PORT":28888,
            "DB_PORT":27017,
            "DB_NAME":'smt_app_db',
            "DB_SMT_COLL":'smt_procucts_coll',
            "DB_USER":'aveen',
            "DB_ADMIN_PWD":'123456',
            "DB_PWD":'123',
            "IS_AUTH":False
         }
##########################

render = render_jinja(os.path.normpath(os.path.dirname(__file__) + '/template'), encoding='utf-8')

http=urllib3.PoolManager()
web.cache=web.Storage()
def get_alibba_auth_url():
    auth_args={
               "client_id":APP_KEY,
               "site":"aliexpress",
               "redirect_uri":LOCAL_APP_URL,
               "state":'test'
               }
    
    def create_sign_str(args):
        '''
                        构造认证请求签名字符串
        '''
        keys=args.keys()
        sorted_keys=sorted(keys)
        temp=[]
        for key in sorted_keys:
            temp.append(''.join((key,str(auth_args[key]))))
        
        sign_str=''.join(temp)
        encry_sign_str=hmac.new(APP_SECRET, sign_str, digestmod=hashlib.sha1).hexdigest().upper() #hmac_sha1加密算法
        return encry_sign_str
    auth_args['_aop_signature']=create_sign_str(auth_args)
    
    url= '?'.join((AUTH_URL,urllib.urlencode(auth_args)))
    return url

def get_token_by_code(code):
    req_args={
              "grant_type":"authorization_code",
              "need_refresh_token":"true",
              "client_id":APP_KEY,
              "client_secret":APP_SECRET,
              "redirect_uri":LOCAL_APP_URL,
              "code":code
              }
    #have 3 methods for request url with post
    params = urllib.urlencode(req_args)
#1
    res =urllib.urlopen(TOKEN_URL, params)
    data=res.read()
#2
#    req=urllib2.Request(TOKEN_URL,params)
#    res = urllib2.urlopen(req)
    
#3
#    http=urllib3.PoolManager()
#    res=http.request('POST',TOKEN_URL,req_args,encode_multipart=False)
#    data=res.data
    
    json_data=json.loads(data)
    return json_data


def get_alidata_by_api(api_name,
                       access_token,
                       protoc_format="param2",
                       api_version="1",
                       api_namspace="aliexpress.open",
                       **api_args):
    '''
        根据接口名和access_token以及接口具体调用相关的参数,
        调用接口,其它参数默认
    '''
    req_args=dict(
                  access_token=access_token,
                  **api_args
                  )
    urlPath='/'.join((protoc_format,api_version,api_namspace,api_name,APP_KEY))
    def create_sign_str():
        '''
                            构造API签名字符串
        '''
        sorted_keys=sorted(req_args.keys())
        temp=[]
        for key in sorted_keys:
            temp.append(''.join((key,str(req_args[key]))))
        req_args_str=''.join(temp)
        sign_str=''.join((urlPath,req_args_str))
        encry_sign_str=hmac.new(APP_SECRET, sign_str, digestmod=hashlib.sha1).hexdigest().upper() #hmac_sha1加密算法

        return encry_sign_str
    
    req_args['_aop_signature']=create_sign_str()
    
    req_url='/'.join((OPEN_API_URL,urlPath))
    res=http.request('GET',req_url,req_args)
    data=res.data
    
    return data
    
    
        
web.config.alibba_auth_url=get_alibba_auth_url()


########################################

def init_dbcontext():
    conn=pymongo.Connection(host=MONGODB['DB_SERVER'], 
                      port=MONGODB['DB_PORT'], 
                      max_pool_size=500,
                      network_timeout=500, 
                      wtimeout=500,
                      tz_aware=True)
    if MONGODB['IS_AUTH']:
        db_admin=conn['admin']
        db_admin.authenticate(MONGODB['DB_USER'],MONGODB['DB_ADMIN_PWD'])
    
    db=conn[MONGODB['DB_NAME']]
    web.ctx.cur_dbconn=conn
    web.ctx.dbcontext=db

def release_dbcontext():
    try:
        if web.ctx.get('cur_dbconn'):
            web.ctx.cur_dbconn.close() 
    except Exception,e:
        print e

urls=(
      '/auth','Auth',
      '/index','Index',
      '/get_smtproducts','SMTProducts'
      )

class Auth(object):
    def GET(self):        
        inputs=web.input()
        code=inputs.get("code",None)
        if not code:
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        
        token_data=get_token_by_code(code)    
        
        web.config.token_data=web.storage(token_data)
#        token_data的的字段有
#        u'aliId
#        u'resource_owner
#        u'access_token
#        u'expires_in
#        u'refresh_token
#        u'refresh_token_timeout
        if web.config.token_data.get('error',None):
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        else:
            raise web.seeother("/index")
        

        
    

class Index(object):
    def GET(self):
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
        datas=coll.find()
        return render.index(items=datas)

        
class SMTProducts(object):
    '''获取SMT上的产品列表,存入数据库
                上架:onSelling ；下架:offline ；审核中:auditing ；审核不通过:editingRequired
    '''
    def GET(self):
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        
        access_token=web.config.token_data.access_token
        res_data=get_alidata_by_api(
                           "api.findProductInfoListQuery",
                            access_token,
                            productStatusType="onSelling",
                            currentPage=1 #默认为第一页
                           )
        tmp_data_lst=[]
        json_data=json.loads(res_data)
        web.cache.product_count=json_data['productCount']
        web.cache.total_page=json_data['totalPage']
        tmp_data_lst.extend(json_data['aeopAEProductDisplayDTOList'])
        
        for i in range(2,web.cache.total_page+1):
            page_data=get_alidata_by_api(
                               "api.findProductInfoListQuery",
                                access_token,
                                productStatusType="onSelling",
                                currentPage=i
                               )
            tmp_data_lst.extend(json.loads(page_data)['aeopAEProductDisplayDTOList'])
        
        products_lst=[]
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
        
        
        for item in tmp_data_lst:
            temp={}
            p_id=item['productId']

            if not coll.find({'smt_productId':p_id}):
                    
                p_info=get_alidata_by_api(
                                       "api.findAeProductById",
                                       access_token,
                                       productId=p_id
                                       )
                temp['smt_productId']=p_id
                temp['smt_productSKUs']=json.loads(p_info)['aeopAeProductSKUs']
    
                coll.insert(temp)
                products_lst.append(temp)
            
            
            
        web.header('Content-type', 'text/html;charset=utf-8')
        return  products_lst



def loadhook():
    try:
        init_dbcontext()
    except Exception,e:
        print e

def unloadhook():
    release_dbcontext()

app = web.application(urls, globals())
app.add_processor(web.loadhook(loadhook))
app.add_processor(web.unloadhook(unloadhook))
application=app.wsgifunc()

if __name__=="__main__":
    app.run()
#    WSGIServer(('0.0.0.0', 8080), application).serve_forever()
    
    
    
    