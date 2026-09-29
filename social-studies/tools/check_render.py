"""Optional Chromium checks. Browser downloads and screenshots stay outside the package."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(root: Path) -> dict:
    evidence=Path('/tmp/social-studies-render-check')
    evidence.mkdir(exist_ok=True)
    tested=[]; errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        version=browser.version
        for width in (1280,390):
            page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
            page.on('pageerror',lambda exc:errors.append(str(exc)))
            for name in ('index.html','study-guide.html','workbook.html','atlas.html','mock-01.html','mock-02.html','mock-03.html','textbook/H04.html','textbook/C11.html'):
                page.goto((root/name).as_uri(),wait_until='load')
                assert page.locator('h1').count()>=1,name
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),(name,width,'horizontal overflow')
                assert page.locator('ruby ruby').count()==0,(name,'nested ruby')
                assert page.evaluate('[...document.images].every(i=>i.complete && i.naturalWidth>0)'),(name,'missing image')
                if name=='index.html':
                    assert page.locator('article[data-lesson]').count()==76
                    assert page.locator('article table').count()==76
                    assert page.locator('article details').count()==228
                    page.locator('#search').fill('地租改正')
                    visible=page.locator('article:not([hidden])').count()
                    assert 0<visible<76,visible
                    page.locator('nav a[href="#F01"]').click()
                    assert page.locator('article[hidden]').count()==0
                    first=page.locator('article#F01 details').first
                    first.locator('summary').click()
                    assert first.get_attribute('open') is not None
                    page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
                    assert page.locator('details[open]').count()==228
                    page.evaluate('window.dispatchEvent(new Event("afterprint"))')
                    assert page.locator('details[open]').count()==1
                    page.locator('article#F01').scroll_into_view_if_needed()
                    page.screenshot(path=str(evidence/f'lesson-{width}.png'))
                if name in ('atlas.html','mock-01.html','textbook/H04.html') and width==1280:
                    if name=='atlas.html':page.locator('img').nth(1).scroll_into_view_if_needed()
                    page.screenshot(path=str(evidence/(name.replace('/','-')+'.png')))
                tested.append({'file':name,'width':width,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()})
            page.close()
        browser.close()
    assert not errors,errors
    result={'status':'passed','engine':'Chromium','version':version,'pages_and_viewports':tested,
            'checks':['76 lesson articles and vocabulary tables','228 collapsible answers','search and navigation reset','answer disclosure and print expansion/restoration','local images decoded','no nested ruby','no page-level horizontal overflow','no JavaScript page errors'],
            'limitations':'Headless Chromium at desktop and phone widths; not physical devices, Safari, or Anki UI.'}
    (root/'BROWSER_TEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    print(json.dumps(run(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
