#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''
import sys
sys.path.append("F:\webroot\python_webapp\smt_app") #only run for in apache
import os
import urllib3
import json
import copy
import web

import pymongo
#from gevent.pywsgi import WSGIServer
from common.conf import *
from common.smt_api import *
from common.common import *




render = render_jinja(os.path.normpath(os.path.dirname(__file__) + '/template'), encoding='utf-8')
render._lookup.filters['imageUrlFilter']=imageUrlFilter

        
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
      '/','redirect login',
      '/auth','Auth',
      '/index','Index',
      '/update_link','UpdateLink',
      '/stock_update','StockUpdate',
      '/login','Login',
      '/logout','Logout',
      '/test','Test'
      )


class Test(object):
    @checklogin
    def GET(self):
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        inputs=web.input()
        id=inputs.get("id",None)
        type=inputs.get('type',None)
        cateid=inputs.get('cateid',None)
        productid=inputs.get('productid',None)
        stock=inputs.get('stock',None)
        
        access_token=web.config.token_data.access_token
        web.header('Content-type', 'text/html;charset=utf-8')
        if id:
            p_info=get_alidata_by_api(
                                   "api.findAeProductById",
                                   access_token,
                                   productId=id
                                   )
            dict_data=json.loads(p_info)
#            del dict_data['detail']
            return dict_data
        
        if type=="products":
            res_data=get_alidata_by_api(
                               "api.findProductInfoListQuery",
                                access_token,
                                productStatusType="onSelling",
                                currentPage=1 #默认为第一页
                               )
            dict_data=json.loads(res_data)
            return res_data
        
        if cateid:
            res_data=get_alidata_by_api(
                               "api.getAttributesResultByCateId",
                                access_token,
                                cateId=cateid,
                               )
            dict_data=json.loads(res_data)
            return res_data
        
        if productid and not stock:
            res_data=get_alidata_by_api(
                               "api.listTbProductByIds",
                                access_token,
                                productIds=productid,
                               )
            dict_data=json.loads(res_data)
            return res_data
        if stock and productid:
            stock=[{u'aeopSKUProperty': [{u'propertyValueId': 29, u'skuPropertyId': 14}], u'skuStock': False, 'skuPrice': u'11.00', 'skuCode': u''}, {u'aeopSKUProperty': [{u'propertyValueId': 193, u'skuPropertyId': 14}], u'skuStock': True, 'skuPrice': u'11.00', 'skuCode': u''}, {u'aeopSKUProperty': [{u'propertyValueId': 350850, u'skuPropertyId': 14}], u'skuStock': True, 'skuPrice': u'11.00', 'skuCode': u''}]
            stock=json.dumps(stock)
            
            res_data=get_alidata_by_api(
                               "api.editProductCidAttIdSku",
                               access_token,
                               productId=productid,
                               productSkus=stock
                               )
            dict_data=json.loads(res_data)
            return res_data
        
class Auth(object):
    @checklogin
    def GET(self):        
        inputs=web.input()
        code=inputs.get("code",None)
        if not code:
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        
        token_data=get_token_by_code(code)    
        
        web.config.token_data=web.storage(token_data)
        if web.config.token_data.get('error',None):
            raise web.seeother(web.config.alibba_auth_url, absolute=True)
        else:
            token_coll=getattr(web.ctx.dbcontext,MONGODB['DB_TOKEN_COLL'])
            tokened=list(token_coll.find())
            if not tokened:
                token_coll.insert(token_data)
            else:
                _id=tokened[0]['_id']
                token_coll.update({'_id':_id},token_data)
            
            raise web.seeother('/index')
        

class Login(object):
    def GET(self):
        if web.ctx.session.user and web.ctx.session.login:
            raise web.seeother('/index')
        
        web.ctx.session.kill()
        return render.login(locals())
    
    def POST(self):
        inputs = web.input()
        user = inputs.get('username', None)
        pwd = inputs.get('password', None)
        if user and pwd:
            if user in USER.keys():
                if USER.get(user)['password']==pwd:
                    web.ctx.session.login = 1
                    web.ctx.session.user = user
                    return web.seeother('/index')
                else:
                    return redirect_HTML("请输入正确的密码!", 3)
            else:
                web.ctx.session.kill()
                return redirect_HTML("请输入正确的用户名!", 3)

        else:
            web.ctx.session.kill()
            return redirect_HTML("请输入用户名名或密码!", 3)

class Logout(object):
    def GET(self):
        web.ctx.session.kill()
        raise web.seeother('/login')

class Index(object):
    @checklogin
    def GET(self):
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
        datas=coll.find()
        isAlibAuth=False
        user_proper={}
        user_proper["user"]=web.ctx.session.user
        user_proper["role"]=USER.get(user_proper["user"])['role']
        
        if web.config.get('token_data',None) and web.config.token_data.get('access_token',None):
            isAlibAuth=True
        return render.index(items=datas,isAlibAuth=isAlibAuth,user=user_proper)

class UpdateLink(object):
    def GET(self):
        inputs=web.input()
        try:
            p_id=int(inputs.get('productId',None));
            newlink=inputs.get('newLink',None)
            if not p_id or not newlink:
                return json.dumps({"msg":"参数错误","status":False})
            
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            data=coll.find_one({'smt_productId':p_id})
            if not data:
                return json.dumps({"msg":"不存在该条数据","status":False})
            coll.update({'smt_productId':p_id},{'$set':{'taobao_link':newlink}})
            
            return json.dumps({"msg":"更新成功","status":True})
        except Exception,e:
            return json.dumps({"msg":"更新失败%s" % str(e),"status":False})



class StockUpdate(object):
    def GET(self):
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            return json.dumps({"msg":"同步SMT库存需要授权","status":False,'ali_auth_url':web.config.alibba_auth_url})
        
        access_token=web.config.token_data.access_token
        inputs=web.input()
        productid=inputs.get("productId",None)
        productSKUs=inputs.get("productSKUs",None)
        if not productid or not productSKUs:
            return json.dumps({"msg":"参数错误","status":False})
        
        try:
            productid=int(productid)
            
            #先调用接口更新smt,再更新本地数据库
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            data=coll.find_one({'smt_productId':productid})
            if not data:
                return json.dumps({"msg":"不存在productid=%s该条数据" % productid,"status":False,"productid":productid})
            
            db_sku_data=copy.deepcopy(data['smt_productSKUs'])

            productSKUs=json.loads(productSKUs)
            
#            print "before update",productSKUs
            for p_sku in productSKUs:
                sku_proper=p_sku['aeopSKUProperty']
                temp_sku_key=''
                for i in sku_proper:
                    temp_sku_key+=str(i['skuPropertyId'])+'_'+str(i['propertyValueId'])
                    
                for db_p_sku in db_sku_data:
                    db_sku_proper=db_p_sku['aeopSKUProperty']
                    temp_db_sku_key=''
                    for i in db_sku_proper:
                        temp_db_sku_key+=str(i['skuPropertyId'])+'_'+str(i['propertyValueId'])
                    if temp_db_sku_key==temp_sku_key:
                        db_p_sku['skuStock']=p_sku['skuStock']
                        p_sku['skuPrice']=db_p_sku['skuPrice']
                        p_sku['skuCode']=db_p_sku['skuCode']
            
#            print "after update",productSKUs
            
                    
            productSKUs=json.dumps(productSKUs)
            
            res_data=get_alidata_by_api(
                               "api.editProductCidAttIdSku",
                               access_token,
                               productId=productid,
                               productSkus=productSKUs
                               )
            res_data=json.loads(res_data)
            
            if not res_data.get('success',None):
                error= res_data['error_message'] if res_data.get('error_message',None) else res_data.get('exception','')

                return json.dumps({"msg":"更新失败:%s" % str(error),"status":False,"productid":productid})
                 
            coll.update({'smt_productId':productid},{'$set':{'smt_productSKUs':db_sku_data}})
            
            return json.dumps({"msg":"更新成功","status":True,"productid":productid})
        except Exception,e:
            return json.dumps({"msg":"更新失败:%s" % str(e),"status":False,"productid":productid})



def loadhook():
    web.header('Content-type', "text/html; charset=utf-8")
    try:
        init_dbcontext()
    except Exception,e:
        print e

def unloadhook():
    release_dbcontext()

def session_hook():
    web.ctx.session=session

web.config.session_parameters['timeout']=3600

app = web.application(urls, globals())
session=web.session.Session(app, web.session.DiskStore('sessions/'), initializer={'login': 0,'user':None})

app.add_processor(web.loadhook(session_hook))
app.add_processor(web.loadhook(loadhook))
app.add_processor(web.unloadhook(unloadhook))
application=app.wsgifunc()

if __name__=="__main__":
    app.run()
#    web.httpserver.runsimple(application, ('0.0.0.0', 8080))
#    WSGIServer(('0.0.0.0', 8080), application).serve_forever()
    
    
    