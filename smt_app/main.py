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
import gevent.monkey 
gevent.monkey.patch_all() 
##有请求是阻塞操作需设置nonkey
##SMTProducts请求处理，本身的server处理同时调用两次,且发生阻塞,导致两个请求写入相同的数据

from web.contrib.template import render_jinja

OPEN_API_URL="http://gw.api.alibaba.com/openapi"

AUTH_URL="http://gw.api.alibaba.com/auth/authorize.htm"

APP_KEY="1067520"
APP_SECRET="PUpMcxJ5om"

TOKEN_URL="https://gw.api.alibaba.com/openapi/http/1/system.oauth2/getToken/"+APP_KEY
LOCAL_APP_URL="http://127.0.0.1:8080/auth"
###################
MONGODB={
            "DB_SERVER":'10.20.14.196',
#            "DB_SERVER":'192.168.1.103',
            "DB_PORT":28888,
#            "DB_PORT":27017,
            "DB_NAME":'smt_app_db',
            "DB_SMT_COLL":'smt_procucts_coll',
            "DB_USER":'aveen',
            "DB_ADMIN_PWD":'123456',
            "DB_PWD":'123',
            "IS_AUTH":True
         }
##########################
def imageUrlFilter(url):
    tmp=url.split('.')
    f='.'.join(tmp[:-1])
    b=tmp[-1]
    return '.'.join([f,'summ',b])


render = render_jinja(os.path.normpath(os.path.dirname(__file__) + '/template'), encoding='utf-8')
render._lookup.filters['imageUrlFilter']=imageUrlFilter

http=urllib3.PoolManager()
web.cache=web.Storage()
web.cache.sku_properid_datas=web.storage()
web.cache.sku_properval_datas=web.storage()
web.cache.cate_attr_datas=web.storage()

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
      '/get_smtproducts','SMTProducts',
      '/test','Test'
      )


class Test(object):
    def GET(self):
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        inputs=web.input()
        id=inputs.get("id",None)
        type=inputs.get('type',None)
        cateid=inputs.get('cateid',None)
        productid=inputs.get('productid',None)
        
        access_token=web.config.token_data.access_token
        web.header('Content-type', 'text/html;charset=utf-8')
        if id:
            
            p_info=get_alidata_by_api(
                                   "api.findAeProductById",
                                   access_token,
                                   productId=id
                                   )
            json_data=json.loads(p_info)
            del json_data['detail']
            return json_data
        
        if type=="products":
            res_data=get_alidata_by_api(
                               "api.findProductInfoListQuery",
                                access_token,
                                productStatusType="onSelling",
                                currentPage=1 #默认为第一页
                               )
            json_data=json.loads(res_data)
            return res_data
        
        if cateid:
            res_data=get_alidata_by_api(
                               "api.getAttributesResultByCateId",
                                access_token,
                                cateId=cateid,
                               )
            json_data=json.loads(res_data)
            return res_data
        
        if productid:
            res_data=get_alidata_by_api(
                               "api.listTbProductByIds",
                                access_token,
                                productIds=productid,
                               )
            json_data=json.loads(res_data)
            return res_data
            

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
            
            raise web.seeother('/index')
        

        
    

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
        
        self.access_token=web.config.token_data.access_token
        res_data=get_alidata_by_api(
                           "api.findProductInfoListQuery",
                            self.access_token,
                            productStatusType="onSelling",
                            currentPage=1 #默认为第一页
                           )
        
        tmp_data_lst=[]
        json_data=json.loads(res_data)
        if not json_data.get('success',None):
            return "调用api.findProductInfoListQuery接口失败"
        web.cache.product_count= ['productCount']
        web.cache.total_page=json_data['totalPage']
        tmp_data_lst.extend(json_data['aeopAEProductDisplayDTOList'])
        
        for i in range(2,web.cache.total_page+1):
            page_data=get_alidata_by_api(
                               "api.findProductInfoListQuery",
                                self.access_token,
                                productStatusType="onSelling",
                                currentPage=i
                               )
            tmp_data_lst.extend(json.loads(page_data)['aeopAEProductDisplayDTOList'])
        

        products_lst=[]
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
        
        for item in tmp_data_lst:
            temp={}
            p_id=item['productId']

            p_info=get_alidata_by_api(
                                   "api.findAeProductById",
                                   self.access_token,
                                   productId=p_id
                                   )
            p_info_json=json.loads(p_info)
            if not json_data.get('success',None):
                return "调用api.findAeProductById 接口失败"
            
            temp['smt_productId']=p_id
            temp['image_url']=p_info_json['imageURLs'].split(';')[0]
            temp['smt_productSKUs']=p_info_json['aeopAeProductSKUs']
            
            cateid=p_info_json['categoryId']
            atrrs=self.get_attr_by_cateid(cateid)
            if not atrrs.get('success',None):
                return "调用api.getAttributesResultByCateId 接口失败"
            
            atrrs_lst=atrrs['attributes']
            
            smt_skus=temp['smt_productSKUs']
            
            for item in smt_skus:
                if item['aeopSKUProperty']:
                    for sku_p in item['aeopSKUProperty']:
                        skuPropertyIdName_en,propertyValues=self.get_skuPropertyId_Name(atrrs_lst,sku_p['skuPropertyId'])
                        propertyValueIdName_en=self.get_propertyValueId_Name(propertyValues,sku_p['propertyValueId'])
                        sku_p['skuPropertyIdName_en']=skuPropertyIdName_en
                        sku_p['propertyValueIdName_en']=propertyValueIdName_en
            
            temp['taobao_link']=self.get_taobaolinkbyId(p_id)
            is_exist=coll.find_one({'smt_productId':p_id})
            if not is_exist:
                coll.insert(temp)
            else:
                coll.update({'smt_productId':p_id},temp)

                
            products_lst.append(temp)
        web.header('Content-type', 'text/html;charset=utf-8')
        return  products_lst
    

    def get_attr_by_cateid(self,cateid):
        '''根据产品的cateId获取属性值'''
        if web.cache.cate_attr_datas.get(cateid,None):
            return web.cache.cate_attr_datas[cateid]
        
        
        res_data=get_alidata_by_api(
                           "api.getAttributesResultByCateId",
                            self.access_token,
                            cateId=cateid,
                           )
        json_data=json.loads(res_data)
        
        web.cache.cate_attr_datas[cateid]=json_data
        return json_data
    
    def get_skuPropertyId_Name(self,attr_lst,skuPropertyId):
        '''
                        根据库存属性id从属性列表中取出相应的skuPropertyIdName_en和propertyValues列表
        '''
        if web.cache.sku_properid_datas.get(skuPropertyId,None):
            return web.cache.sku_properid_datas[skuPropertyId]
        
        for item in attr_lst:
            if item['id']==skuPropertyId:
                skuPropertyIdName_en=item['names']['en']
                if item.get('values',None):
                    propertyValues=item['values']
                break
            
        web.cache.sku_properid_datas[skuPropertyId]=(skuPropertyIdName_en,propertyValues)
        return (skuPropertyIdName_en,propertyValues)
            
    def get_propertyValueId_Name(self,propertyValues,propertyValueId):
        if web.cache.sku_properval_datas.get(propertyValueId,None):
            return web.cache.sku_properval_datas[propertyValueId]
        
        for item in propertyValues:
            if propertyValueId==item['id']:
                propertyValueIdName_en=item['names']['en']
                web.cache.sku_properval_datas[propertyValueId]=propertyValueIdName_en
                return propertyValueIdName_en
        
    def get_taobaolinkbyId(self,p_id):
        res_data=get_alidata_by_api(
                           "api.listTbProductByIds",
                            self.access_token,
                            productIds=p_id,
                           )
        json_data=json.loads(res_data)
        if isinstance(json_data, list) and json_data:
            link=json_data[0].get('detailUrl',None)
            return link




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
#    web.httpserver.runsimple(application, ('0.0.0.0', 8080))
#    WSGIServer(('0.0.0.0', 8080), application).serve_forever()
    
    
    