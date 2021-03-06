﻿#coding=utf-8
'''
Created on 2014-10-24

@author: Administrator
'''
import sys
import os
sys.path.append(os.path.dirname(__file__))#only running for in apache 
import traceback

import urllib3
import json
import copy
import web

import pymongo
#import gevent
#from gevent.pywsgi import WSGIServer
from common.conf import *
from common.smt_api import *
from common.common import *




render = render_jinja(os.path.normpath(os.path.dirname(__file__) + '/template'), encoding='utf-8')
render._lookup.filters['imageUrlFilter']=imageUrlFilter

        
web.config.alibba_auth_url=get_alibba_auth_url()



web.cache=web.Storage()
web.cache.cate_attr_datas=web.storage()
web.cache.sku_properid_datas=web.storage()
web.cache.sku_properval_datas=web.storage()
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
      '/product_update','ProductUpdate',
      '/product_offline','ProductOffline',
      '/bulk_get_products','BulkProductsDown',
      '/search_product','ProductSearch',
      
      '/login','Login',
      '/logout','Logout',
      '/test','Test',
      '/aveenzhou','Zhou'
      )
class Zhou(object):
    def GET(self):
        return render.resume()

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
        offid=inputs.get('offid',None)
        access_token=web.config.token_data.access_token
        web.header('Content-type', 'text/html;charset=utf-8')
        
        if offid:
            res_data=get_alidata_by_api(
                               "api.offlineAeProduct",
                               access_token,
                               productIds=offid
                               )
            return res_data
        
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
            try:
                token_coll=getattr(web.ctx.dbcontext,MONGODB['DB_TOKEN_COLL'])
                tokened=list(token_coll.find())
                if not tokened:
                    token_coll.insert(token_data)
                else:
                    _id=tokened[0]['_id']
                    token_coll.update({'_id':_id},token_data)
            except Exception,e:
                pass
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
    
    PAGE_NUM=10
    @checklogin
    def GET(self):
        try:
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            counts=coll.find({}).count()
            datas=coll.find({}).sort('smt_productId',1).limit(self.PAGE_NUM)
        except Exception,e:
            print "mongo error",e
            datas=[]
        isAlibAuth=False
        user_proper={}
        user_proper["user"]=web.ctx.session.user
        user_proper["role"]=USER.get(user_proper["user"])['role']
        
        if web.config.get('token_data',None) and web.config.token_data.get('access_token',None):
            isAlibAuth=True
        
        return render.index(items=datas,isAlibAuth=isAlibAuth,user=user_proper,counts=counts)

    def POST(self):
        if not web.ctx.session.user:
            return json.dumps({'redirect':True})
        user_proper={}
        user_proper["user"]=web.ctx.session.user
        user_proper["role"]=USER.get(user_proper["user"])['role']
        try:
            inputs=web.input()
            page=inputs.get('page',1)
            skip_num=(int(page)-1)*self.PAGE_NUM
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            datas=coll.find({}).sort('smt_productId',1).skip(skip_num).limit(self.PAGE_NUM);
        except Exception,e:
            print "mongo error",e
            datas=[]
        htmldata=None
        if datas:
            htmldata=render.ajaxpage(items=datas,user=user_proper,skipnum=skip_num)
        
        return json.dumps({'htmldata':htmldata,'page':page})

        
    

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
    def POST(self):
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
#                        db_p_sku['skuStock']=p_sku['skuStock']
                        db_p_sku['ipmSkuStock']=p_sku['ipmSkuStock']
                        p_sku['skuPrice']=db_p_sku['skuPrice']
                        p_sku['skuCode']=db_p_sku['skuCode']
            
#            print "after update",productSKUs
            
                    
            productSKUs=json.dumps(productSKUs)
            
            res_data=get_alidata_by_api(
                               "api.editProductCidAttIdSku",
                               access_token,
                               productId=str(productid),
                               productSkus=productSKUs
                               )
            
            res_data=json.loads(res_data)
            
            if not res_data.get('success',None):
                error= res_data['error_message'] if res_data.get('error_message',None) else res_data.get('exception','')
                print error
                error_data={"msg":"更新失败:%s" % str(error),"status":False,"productid":productid}
                if res_data.get('error_code',None)=='401':
                    error_data['ali_auth_url']=web.config.alibba_auth_url
                return json.dumps(error_data)
                 
            coll.update({'smt_productId':productid},{'$set':{'smt_productSKUs':db_sku_data}})
            
            return json.dumps({"msg":"更新成功","status":True,"productid":productid})
        except Exception,e:
            print traceback.format_exc()
            return json.dumps({"msg":"更新失败:%s" % str(e),"status":False,"productid":productid})
        
        

class ProductUpdate(object):
    def GET(self):
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            return json.dumps({"msg":"更新产品需要授权","status":False,'ali_auth_url':web.config.alibba_auth_url})
        self.access_token=web.config.token_data.access_token
        inputs=web.input()
        productid=inputs.get("productId",None)
    
        if not productid:
            return json.dumps({"msg":"参数错误","status":False})
        
        try:
            productid=int(productid)
            p_info=self._get_product_byid(str(productid))
            
            if not p_info.get('success',None):
                return get_error_msg(p_info,productid)
            
            p_states=PRODUCT_STATE.keys()
            p_states.remove('onSelling')
            noSelling=p_states

            if p_info['productStatusType'] in noSelling:
                res= {"msg":"产品%s处于%s" % (productid,PRODUCT_STATE.get(p_info['productStatusType'],p_info['productStatusType'])),
                        "status":False,
                        "productid":productid}
                return json.dumps(res)
            
            temp={}
            temp['smt_productId']=productid
            temp['image_url']=p_info['imageURLs'].split(';')[0]
            temp['smt_productSKUs']=p_info['aeopAeProductSKUs']
            
            cateid=p_info['categoryId']
            atrrs=self._get_attr_by_cateid(cateid)
            if not atrrs.get('success',None):
                return get_error_msg(atrrs,productid)
            
            atrrs_lst=atrrs['attributes']
            
            smt_skus=temp['smt_productSKUs']
            
            for item in smt_skus:
                if item['aeopSKUProperty']:
                    for sku_p in item['aeopSKUProperty']:
                        skuPropertyIdName_en,propertyValues=self._get_skuPropertyId_Name(atrrs_lst,sku_p['skuPropertyId'])
                        propertyValueIdName_en=self._get_propertyValueId_Name(propertyValues,sku_p['propertyValueId'])
                        sku_p['skuPropertyIdName_en']=skuPropertyIdName_en
                        sku_p['propertyValueIdName_en']=propertyValueIdName_en
            
            tbdata=self._get_taobaolinkbyId(str(productid))
            if isinstance(tbdata, list) and tbdata:
                link=tbdata[0].get('detailUrl',None)
                temp['taobao_link']= link
            
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            is_exist=coll.find_one({'smt_productId':productid})
            if not is_exist:
                coll.insert(temp)
#                print "Get a Data:",temp
                return json.dumps({"msg":"获取成功","status":True,"productid":productid})
            else:

                coll.update({'smt_productId':productid},{'$set':temp})
#                print "Update a Data:",temp
                return json.dumps({"msg":"更新成功","status":True,"productid":productid})
        except Exception,e:
            print traceback.format_exc()

            return json.dumps({"msg":"操作失败:%s" % str(e),"status":False,"productid":productid})
        
    def _get_product_byid(self,p_id):
        
        p_info=get_alidata_by_api(
                               "api.findAeProductById",
                               self.access_token,
                               productId=p_id
                               )
        json_data=json.loads(p_info)

        return json_data
    
    def _get_attr_by_cateid(self,cateid):
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
        
    def _get_skuPropertyId_Name(self,attr_lst,skuPropertyId):
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
            
    def _get_propertyValueId_Name(self,propertyValues,propertyValueId):
        if web.cache.sku_properval_datas.get(propertyValueId,None):
            return web.cache.sku_properval_datas[propertyValueId]
        
        for item in propertyValues:
            if propertyValueId==item['id']:
                propertyValueIdName_en=item['names']['en']
                web.cache.sku_properval_datas[propertyValueId]=propertyValueIdName_en
                return propertyValueIdName_en
        
    def _get_taobaolinkbyId(self,p_id):
        res_data=get_alidata_by_api(
                           "api.listTbProductByIds",
                            self.access_token,
                            productIds=p_id,
                           )
        json_data=json.loads(res_data)
        return json_data





class ProductOffline(object):
    def GET(self):
        
        
        inputs=web.input()
        p_id=inputs.get("productId",None)
        if not p_id:
            return json.dumps({"msg":"参数错误","status":False})
        
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            return json.dumps({"msg":"操作需要授权","status":False,'ali_auth_url':web.config.alibba_auth_url})
        self.access_token=web.config.token_data.access_token
        try:
            p_id=int(p_id)
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            is_db_exist=coll.find_one({'smt_productId':p_id})
            if not is_db_exist:
                return json.dumps({"msg":"产品%s下架成功" % p_id,"status":True,"productid":p_id})
            
            res_data=get_alidata_by_api(
                               "api.offlineAeProduct",
                               self.access_token,
                               productIds=str(p_id)
                               )
            json_data=json.loads(res_data)
            
            error_code=json_data.get('error_code',None)
            error_code=str(error_code)
            if error_code and error_code in ('12001024','12001026'):
                #12001024    根据id查找不到对应的产品
                #12001026    所有传入产品id的产品都在下架状态
                coll.remove({'smt_productId':p_id})
                return json.dumps({"msg":json_data['error_message'],"status":True,"productid":p_id})
            
            if error_code and error_code in ('12001030','12001025'):
                #12001030    传入的产品有在活动中的，不能操作
                #12001025    根据id查找到的产品不归属于该用户
                return json.dumps({"msg":"操作失败:%s" % json_data['error_message'],"status":False,"productid":p_id})
            
            if not json_data.get('success',None):

                return get_error_msg(json_data,p_id)
            
            coll.remove({'smt_productId':p_id})
            return json.dumps({"msg":"产品%s下架成功" % p_id,"status":True,"productid":p_id})
            
        except Exception,e:
            return json.dumps({"msg":"操作失败:%s" % str(e),"status":False,"productid":p_id})
            

class ProductSearch(object):
    def GET(self):
        if not web.ctx.session.user:
            return json.dumps({'redirect':True,"status":False})
        user_proper={}
        user_proper["user"]=web.ctx.session.user
        user_proper["role"]=USER.get(user_proper["user"])['role']
        
        inputs=web.input()
        
        p_id=inputs.get("productId",None)
        if not p_id:
            return json.dumps({"htmldata":None,"status":True})
        try:
            p_id=int(p_id)
            coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])
            datas=coll.find({'smt_productId':p_id})
            if not datas:
                return json.dumps({"msg":"产品%s不存在" % p_id,"status":False,"productid":p_id})
            
            htmldata=render.ajaxpage(items=datas,user=user_proper,skipnum=None)
            return json.dumps({'htmldata':htmldata,"status":True})
        except Exception,e:
            return json.dumps({"msg":"操作失败:%s" % str(e),"status":False,"productid":p_id})

#批量下载smt产品添加到本地

    
class BulkProductsDown(object):
    @checklogin
    def GET(self):

        web.header('Content-type','text/html')
        web.header('Transfer-Encoding','chunked')  
        
        if not web.config.get('token_data',None) or web.config.token_data.get('error',None):
            yield "<a href=\"%s\">需要授权 </a></br>" % LOCAL_APP_URL
            return
            
        self.access_token=web.config.token_data.access_token
        res_data=get_alidata_by_api(
                           "api.findProductInfoListQuery",
                            self.access_token,
                            productStatusType="onSelling",
                            currentPage=1 #默认为第一页
                           )
        
        tmp_data_lst=[]
        dict_data=json.loads(res_data)
        
        if not dict_data.get('success',None):
            yield "调用api.findProductInfoListQuery接口失败</br>"
            return
        
        web.cache.total_page=dict_data['totalPage']
        tmp_data_lst.extend(dict_data['aeopAEProductDisplayDTOList'])
        
        for i in range(2,web.cache.total_page+1):
            page_data=get_alidata_by_api(
                               "api.findProductInfoListQuery",
                                self.access_token,
                                productStatusType="onSelling",
                                currentPage=i
                               )
            page_data_dict=json.loads(page_data)
            if not page_data_dict.get('success',None):
                print page_data_dict
                yield  "调用api.findProductInfoListQuery 接口失败"
                return
            tmp_data_lst.extend(page_data_dict['aeopAEProductDisplayDTOList'])
        
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])

        for item in tmp_data_lst:
            temp={}
            p_id=int(item['productId'])

            p_info=get_alidata_by_api(
                                   "api.findAeProductById",
                                   self.access_token,
                                   productId=p_id
                                   )
            p_info_dict=json.loads(p_info)
            if not p_info_dict.get('success',None):
                yield "调用api.findAeProductById 接口失败</br>"
                return
            temp['smt_productId']=p_id
            temp['image_url']=p_info_dict['imageURLs'].split(';')[0]
            temp['smt_productSKUs']=p_info_dict['aeopAeProductSKUs']
            
            cateid=p_info_dict['categoryId']
            atrrs=self.get_attr_by_cateid(cateid)
            
            if not atrrs.get('success',None):
                yield "调用api.getAttributesResultByCateId 接口失败</br>"
                return
            
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
                yield "Get Data: %s</br>" % str(temp['smt_productId'])
            else:
                if is_exist.get('taobao_link',None) and not temp['taobao_link']:
                    temp['taobao_link']=is_exist['taobao_link']
                coll.update({'smt_productId':p_id},{'$set':temp})
                yield "Update Data: %s</br>" % str(temp['smt_productId'])
        
        yield "Over!!!</br>"

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
    web.header('Content-type', "text/html; charset=utf-8")
    if web.ctx.path != "/aveenzhou":
        try:
            init_dbcontext()
        except Exception,e:
            print e

def unloadhook():
    release_dbcontext()

def session_hook():
    web.ctx.session=session
web.config.session_parameters['cookie_name']='stock_session_id'
web.config.session_parameters['timeout']=18000# 5hours

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
    
    
    