#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''
import os
import urllib3
import json

import web

import pymongo
from gevent.pywsgi import WSGIServer
from conf import *
from smt_api import *


def imageUrlFilter(url):
    tmp=url.split('.')
    f='.'.join(tmp[:-1])
    b=tmp[-1]
    return '.'.join([f,'summ',b])

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
      '/auth','Auth',
      '/index','Index',
      '/update_link','UpdateLink',
      '/stock_update','StockUpdate',
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
            del dict_data['detail']
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
        
        if productid:
            res_data=get_alidata_by_api(
                               "api.listTbProductByIds",
                                access_token,
                                productIds=productid,
                               )
            dict_data=json.loads(res_data)
            return res_data
        if stock and productid:
            get_alidata_by_api(
                               "api.editProductCidAttIdSku",
                               access_token,
                               productIds=productid,
                               
                               )
            

class Auth(object):
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
        

        
    

class Index(object):
    def GET(self):
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
        datas=coll.find()
        return render.index(items=datas)

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
        pass



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
    
    
    