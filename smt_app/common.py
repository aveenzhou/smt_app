#coding=utf-8
'''
Created on 2014-11-5

@author: Administrator
'''
import web

def imageUrlFilter(url):
    tmp=url.split('.')
    f='.'.join(tmp[:-1])
    b=tmp[-1]
    return '.'.join([f,'summ',b])




def redirect_HTML(msg, seconds):
    mis = seconds * 1000
    return '''
            %s...<span id="count">%s</span>
            <script type="text/javascript">
                function refresh_count(){
                        var orign=document.getElementById('count').innerHTML;
                        num=parseInt(orign);
                        document.getElementById('count').innerHTML =num-1;
                }
                setInterval('refresh_count()',1000);
                setTimeout("window.location.href='/login'",%s);
            </script>''' % (msg, seconds, mis)
            
            
            
def checklogin(func):
    def wraper(*args,**kwargs):
        if not web.ctx.session.user and not web.ctx.session.login:
            web.ctx.session.kill()
            return redirect_HTML("会话已过期，重新登录", 3)
        
        return func(*args,**kwargs)
        
    return wraper
    
            