#coding=utf-8
'''
Created on 2014-11-1

@author: aveenzhou
'''
import web
from common.conf import *
from common.smt_api import *
from main import init_dbcontext,release_dbcontext


class SMTProducts(object):
    '''获取SMT上的产品列表,存入数据库
                上架:onSelling ；下架:offline ；审核中:auditing ；审核不通过:editingRequired
    '''
    def __init__(self):
        init_dbcontext()
        web.cache=web.Storage()
        web.cache.sku_properid_datas=web.storage()
        web.cache.sku_properval_datas=web.storage()
        web.cache.cate_attr_datas=web.storage()
        self.access_token=''
        self.get_token_from_db()
    
    def get_token_from_db(self):
        token_coll=getattr(web.ctx.dbcontext,MONGODB['DB_TOKEN_COLL'])

        data=list(token_coll.find())

        if data and len(data)==1:
            token_data=data[0]
            if token_data.get('error',None):
                print "token数据不正确，重新获取"
                return 
            self.access_token=token_data['access_token']
        else:
            print "token数据不存在，重新获取"
            
    
    def get_alie_data(self):
        if not self.access_token:
            print "token数据不存在，重新获取"
        
        res_data=get_alidata_by_api(
                           "api.findProductInfoListQuery",
                            self.access_token,
                            productStatusType="onSelling",
                            currentPage=1 #默认为第一页
                           )
        
        tmp_data_lst=[]
        dict_data=json.loads(res_data)
        
        if not dict_data.get('success',None):
            print dict_data
            print "调用api.findProductInfoListQuery接口失败"
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
            tmp_data_lst.extend(json.loads(page_data)['aeopAEProductDisplayDTOList'])
        
        coll=getattr(web.ctx.dbcontext,MONGODB['DB_SMT_COLL'])

        for item in tmp_data_lst:
            temp={}
            p_id=str(item['productId'])

            p_info=get_alidata_by_api(
                                   "api.findAeProductById",
                                   self.access_token,
                                   productId=p_id
                                   )
            p_info_dict=json.loads(p_info)
            if not p_info_dict.get('success',None):
                print "调用api.findAeProductById 接口失败"
            
            temp['smt_productId']=p_id
            temp['image_url']=p_info_dict['imageURLs'].split(';')[0]
            temp['smt_productSKUs']=p_info_dict['aeopAeProductSKUs']
            
            cateid=p_info_dict['categoryId']
            atrrs=self.get_attr_by_cateid(cateid)
            if not atrrs.get('success',None):
                print "调用api.getAttributesResultByCateId 接口失败"
            
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
                print "Get Data:",temp
            else:
                if is_exist['taobao_link'] and not temp['taobao_link']:
                    temp['taobao_link']=is_exist['taobao_link']
                coll.update({'smt_productId':p_id},{'$set':temp})
                print "Update Data:",temp
        
        print "Over!!!"
        release_dbcontext()

    

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
        
        
if __name__=="__main__":
    smt=SMTProducts()
    smt.get_alie_data()
