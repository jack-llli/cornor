import asyncio
from playwright.async_api import async_playwright, Page
from datetime import datetime
import json
from typing import List, Dict
import os
import re

class CornerKickScraper:
    def __init__(self):
        # 基础配置
        self.base_url = "https://www.599.com"
        self.corner_data = {}           # 存储所有事件（包括角球）
        self.corner_only_data = {}      # 只存储角球事件（用于专门统计和保存）
        self.corner_file = 'corner_only_data.json'
        self.browser = None
        self.context = None
        self.monitoring_pages = {}      # {match_id: page}
        self.refresh_interval = 300     # 每5分钟扫描一次新比赛
        self.close_delay = 200          # 0:0比分或无事件列表时关闭延时（秒）
      
    async def init_browser(self, headless=True):  # 🔴 修改：默认改为 True（无头模式）
        """初始化浏览器（添加反检测参数）- 无头模式"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,  # 🔴 使用无头模式
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certificate-errors',
                '--ignore-certificate-errors-spki-list',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            permissions=['geolocation']
        )
        # 额外注入脚本绕过常见检测
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        """)
        print("✓ 浏览器已启动（无头模式）")  # 🔴 添加提示


    
    async def close_browser(self):
        """优雅关闭所有页面和浏览器"""
        for page in self.monitoring_pages.values():
            try:
                await page.close()
            except:
                pass
      
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()



async def get_live_matches(self) -> List[Dict]:
        """获取进行中的比赛列表（排除未开）"""
        page = await self.context.new_page()
      
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在扫描比赛列表...")
            await page.goto(f"{self.base_url}/live/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)  # 等待动态加载
            
            matches_data = await page.evaluate('''() => {
                const results = [];
                // 多种可能的行选择器
                let rows = document.querySelectorAll('.match, tr[data-mid], table tr[data-mid], .live-item, .game-row');
                if (rows.length === 0) {
                    rows = document.querySelectorAll('tr');
                }
                
                rows.forEach((row, index) => {
                    try {
                        const tds = row.querySelectorAll('td, div');
                        if (tds.length < 4) return;
                        
                        let status = '';
                        let home = '';
                        let away = '';
                        let score = '';
                        let href = '';
                        
                        const statusPatterns = ['上半场', '下半场', '中场', '完场', '加时', '点球', '未开'];
                        const timePattern = /^\\d+\\s*['′′]\\s*$/;
                        const scorePattern = /^\\d+\\s*[:：]\\s*\\d+$/;
                        
                        // 提取状态、比分
                        for (let i = 0; i < tds.length; i++) {
                            const text = tds[i].innerText.trim();
                            if (statusPatterns.some(p => text.includes(p)) || timePattern.test(text)) {
                                status = text;
                            }
                            if (scorePattern.test(text.replace(/\\s/g, ''))) {
                                score = text;
                            }
                        }
                        
                        // 提取链接和队伍名称
                        const links = row.querySelectorAll('a[href*="/live/"]');
                        for (const link of links) {
                            const h = link.getAttribute('href');
                            if (h && h.includes('/live/') && !h.includes('odds')) {
                                href = h;
                                const linkText = link.innerText.trim();
                                if (linkText && linkText.length > 1 && !scorePattern.test(linkText)) {
                                    if (!home) home = linkText;
                                    else if (!away && linkText !== home) away = linkText;
                                }
                            }
                        }
                        
                        // fallback 提取队伍名
                        if (!home || !away) {
                            for (let i = 0; i < tds.length; i++) {
                                const text = tds[i].innerText.trim();
                                if (text.length > 1 && text.length < 40 &&
                                    !statusPatterns.some(p => text.includes(p)) &&
                                    !timePattern.test(text) &&
                                    !scorePattern.test(text.replace(/\\s/g, '')) &&
                                    !/^\\d{1,2}:\\d{2}$/.test(text) &&
                                    text !== 'VS') {
                                    if (!home) home = text;
                                    else if (!away && text !== home) away = text;
                                }
                            }
                        }
                        
                        if (href && home && away) {
                            results.push({
                                index: index,
                                status: status,
                                home: home,
                                away: away,
                                score: score,
                                href: href
                            });
                        }
                    } catch (e) {}
                });
                return results;
            }''')
            
            print(f"页面共找到 {len(matches_data)} 场比赛")
            matches = []
            
            for data in matches_data:
                # 严格排除未开
                if '未开' in data['status'] or '未开' in data.get('home', '') + data.get('away', '') or 'VS' in data.get('home', '') + data.get('away', ''):
                    continue
                
                match_url = f"{self.base_url}{data['href']}" if data['href'].startswith('/') else data['href']
                match_id = data['href'].split('/')[-2] if '/' in data['href'] else f"match_{len(matches)}"
                
                match_info = {
                    'id': match_id,
                    'url': match_url,
                    'home': data['home'],
                    'away': data['away'],
                    'score': data['score'] or '0:0',
                    'status': data['status'] or '进行中'
                }
                
                matches.append(match_info)
                print(f"✓ [{match_id}] {match_info['home']} vs {match_info['away']} ({match_info['status']}) {match_info['score']}")
            
            await page.close()
            return matches
            
        except Exception as e:
            print(f"获取比赛列表出错: {str(e)}")
            await page.close()
            return []


async def check_target_element_exists(self, page: Page) -> bool:
        """检查是否存在事件/动画直播区域"""
        try:
            await asyncio.sleep(2)
            has_event = await page.evaluate('''() => {
                const selectors = [
                    '[class*="event"]', '[class*="live-animation"]', '[class*="timeline"]',
                    '.event-list', '.animation', '#animation', '[id*="live"]'
                ];
                for (const sel of selectors) {
                    if (document.querySelector(sel)) return true;
                }
                // 文本兜底
                return document.body.innerText.includes('角球') || 
                       document.body.innerText.includes('获得角球') ||
                       document.body.innerText.includes('上半场') ||
                       document.body.innerText.includes('下半场');
            }''')
            return has_event
        except:
            return False
  
    async def extract_team_names_and_score_dom(self, page: Page) -> Dict:
        """通过DOM方式提取队伍名和比分（多策略fallback）"""
        try:
            info = await page.evaluate('''() => {
                let home = '', away = '', score = '', status = '';
                
                // 策略1: 常见比分元素
                const scoreSelectors = ['.score', '[class*="score"]', '.match-score', '.live-score'];
                for (const sel of scoreSelectors) {
                    const elem = document.querySelector(sel);
                    if (elem) {
                        const text = elem.innerText.trim();
                        if (/^\\d+\\s*[:：]\\s*\\d+$/.test(text.replace(/\\s/g, ''))) {
                            score = text;
                            // 查找相邻队伍名
                            const parent = elem.closest('div, .match-info, .header');
                            if (parent) {
                                const texts = parent.innerText.split('\\n').map(t => t.trim()).filter(t => t);
                                for (const t of texts) {
                                    if (t.length > 1 && t.length < 30 && !/\\d+[:：]\\d+/.test(t) && !/^\\d+['′′]$/.test(t)) {
                                        if (!home) home = t;
                                        else if (!away && t !== home) away = t;
                                    }
                                }
                            }
                        }
                    }
                }
                
                // 策略2: 主客队专用class
                const homeElems = document.querySelectorAll('[class*="home"], [class*="left"], [class*="host"], [class*="主队"]');
                const awayElems = document.querySelectorAll('[class*="away"], [class*="right"], [class*="guest"], [class*="客队"]');
                
                for (const el of homeElems) {
                    const text = el.innerText.trim();
                    if (text && text.length > 1 && text.length < 30 && !/\\d+[:：]\\d+/.test(text)) {
                        if (!home) home = text.split('\\n')[0];
                    }
                }
                for (const el of awayElems) {
                    const text = el.innerText.trim();
                    if (text && text.length > 1 && text.length < 30 && !/\\d+[:：]\\d+/.test(text)) {
                        if (!away) away = text.split('\\n')[0];
                    }
                }
                
                // 策略3: 查找所有可能的时间状态
                const timeElems = document.querySelectorAll('span, div');
                for (const el of timeElems) {
                    const text = el.innerText.trim();
                    if (/^\\d+['′′]$/.test(text)) {
                        status = text;
                        break;
                    }
                }
                if (document.body.innerText.includes('中场')) status = '中场';
                
                return { home, away, score: score || '', status: status || '' };
            }''')
            return info
        except:
            return {'home': '', 'away': '', 'score': '', 'status': ''}



async def extract_corner_events_dom(self, page: Page) -> List[str]:
        """核心修改：使用DOM方式精确提取角球事件"""
        try:
            events = await page.evaluate('''() => {
                const cornerEvents = [];
                const seen = new Set();
                
                // 多种可能的事件列表容器选择器
                const containerSelectors = [
                    '.event-list', '.timeline', '[class*="event"]', '[class*="live-animation"]',
                    '#animation', '.match-events', '.live-text', 'div[class*="text"]'
                ];
                
                let container = null;
                for (const sel of containerSelectors) {
                    container = document.querySelector(sel);
                    if (container) break;
                }
                if (!container) container = document.body;  // fallback
                
                // 查找所有可能的事件行（div, li, p, span等）
                const rows = container.querySelectorAll('div, li, p, span, tr');
                
                let currentTime = '';
                for (const row of rows) {
                    const text = row.innerText.trim();
                    if (!text) continue;
                    
                    // 提取时间（单独的行或元素）
                    if (/^\\d+['′′′]$/.test(text)) {
                        currentTime = text;
                        continue;
                    }
                    
                    // 判断是否角球事件
                    if (text.includes('角球') && (text.includes('获得') || text.includes('角球'))) {
                        let fullEvent = text;
                        if (currentTime) {
                            fullEvent = currentTime + ' ' + text;
                            currentTime = '';  // 用完清空
                        } else if (/^\\d+['′′′]/.test(text.substring(0, 6))) {
                            // 事件自带时间
                            fullEvent = text;
                        }
                        
                        // 标准化并去重
                        const normalized = fullEvent.trim();
                        if (normalized.length < 100 && !seen.has(normalized)) {
                            seen.add(normalized);
                            cornerEvents.push(normalized);
                        }
                    }
                    
                    // 如果行太长，重置时间
                    if (text.length > 100) {
                        currentTime = '';
                    }
                }
                
                // 补充策略：查找包含"角球"的所有元素
                const cornerElems = container.querySelectorAll('*');
                for (const elem of cornerElems) {
                    const text = elem.innerText.trim();
                    if (text.includes('角球') && text.includes('获得') && text.length < 100) {
                        let full = text;
                        // 查找前一个兄弟元素是否是时间
                        if (elem.previousElementSibling) {
                            const prevText = elem.previousElementSibling.innerText.trim();
                            if (/^\\d+['′′′]$/.test(prevText)) {
                                full = prevText + ' ' + text;
                            }
                        }
                        const normalized = full.trim();
                        if (!seen.has(normalized)) {
                            seen.add(normalized);
                            cornerEvents.push(normalized);
                        }
                    }
                }
                
                return cornerEvents;
            }''')
            return events
        except Exception as e:
            print(f"DOM提取角球事件出错: {e}")
            return []



async def extract_all_events_dom(self, page: Page) -> List[str]:
        """使用DOM方式提取所有事件（进球、角球、黄牌等）"""
        try:
            events = await page.evaluate('''() => {
                const allEvents = [];
                const seen = new Set();
                
                const containerSelectors = [
                    '.event-list', '.timeline', '[class*="event"]', '[class*="live-animation"]',
                    '#animation', '.match-events', '.live-text', 'div[class*="text"]'
                ];
                
                let container = null;
                for (const sel of containerSelectors) {
                    container = document.querySelector(sel);
                    if (container) break;
                }
                if (!container) container = document.body;
                
                const rows = container.querySelectorAll('div, li, p, span, tr');
                
                let currentTime = '';
                for (const row of rows) {
                    const text = row.innerText.trim();
                    if (!text) continue;
                    
                    if (/^\\d+['′′′]$/.test(text)) {
                        currentTime = text;
                        continue;
                    }
                    
                    // 有效事件描述（长度合理且包含足球术语）
                    if (text.length > 3 && text.length < 100 &&
                        (text.includes('球') || text.includes('进球') || text.includes('角球') ||
                         text.includes('黄牌') || text.includes('红牌') || text.includes('换人'))) {
                        let fullEvent = text;
                        if (currentTime) {
                            fullEvent = currentTime + ' ' + text;
                            currentTime = '';
                        } else if (/^\\d+['′′′]/.test(text.substring(0, 6))) {
                            fullEvent = text;
                        }
                        
                        const normalized = fullEvent.trim();
                        if (!seen.has(normalized)) {
                            seen.add(normalized);
                            allEvents.push(normalized);
                        }
                    }
                    
                    if (text.length > 100) {
                        currentTime = '';
                    }
                }
                
                return allEvents;
            }''')
            return events
        except Exception as e:
            print(f"DOM提取所有事件出错: {e}")
            return []
  
    def save_corner_data(self):
        """保存角球专用数据到JSON（覆盖式）"""
        try:
            output_data = {
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_matches': len(self.corner_only_data),
                'total_corners': 0,
                'matches': {}
            }
            
            total_corners = 0
            for match_id, data in self.corner_only_data.items():
                corners = data.get('corners', [])
                home_corners = len([c for c in corners if '主队' in c or 'home' in c.lower()])
                away_corners = len([c for c in corners if '客队' in c or 'away' in c.lower()])
                
                output_data['matches'][match_id] = {
                    'match_info': data['match_info'],
                    'stats': {
                        'total': len(corners),
                        'home': home_corners,
                        'away': away_corners
                    },
                    'events': corners
                }
                total_corners += len(corners)
            
            output_data['total_corners'] = total_corners
            
            with open(self.corner_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"✓ 角球数据已保存到 {self.corner_file}")
            
        except Exception as e:
            print(f"保存角球数据失败: {str(e)}")




def print_live_table(self):
        """打印实时监控表格"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "="*130)
        print("足球角球实时监控系统 (DOM解析版 - 无头模式)".center(130))  # 🔴 添加无头模式标识
        print("="*130)
        print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"监控比赛数: {len(self.monitoring_pages)} | 角球数据文件: {self.corner_file}")
        print("="*130)
        
        if not self.corner_data:
            print("暂无数据".center(130))
            return
        
        header = f"{'ID':<12} {'主队':<25} {'客队':<25} {'比分':<10} {'状态':<10} {'总事件':<8} {'角球数':<8}"
        print(header)
        print("-"*130)
        
        total_events = 0
        total_corners = 0
        for match_id, data in sorted(self.corner_data.items()):
            info = data['match_info']
            events = data['events']
            corners = self.corner_only_data.get(match_id, {}).get('corners', [])
            
            home = info['home'][:23]
            away = info['away'][:23]
            
            print(f"{match_id:<12} {home:<25} {away:<25} {info['score']:<10} {info['status']:<10} {len(events):<8} {len(corners):<8}")
            
            total_events += len(events)
            total_corners += len(corners)
        
        print("-"*130)
        print(f"总计: {len(self.corner_data)} 场比赛 | {total_events} 总事件 | {total_corners} 总角球")
        print("="*130)
        
        # 详细角球列表
        if total_corners > 0:
            print("\n⚽ 近期角球事件详情:")
            print("="*130)
            for match_id, data in sorted(self.corner_only_data.items()):
                corners = data.get('corners', [])
                if corners:
                    info = data['match_info']
                    print(f"\n🏆 {info['home']} vs {info['away']} ({info['score']})")
                    for i, event in enumerate(corners[-10:], 1):  # 只显示最近10个
                        print(f"  {i:>2}. {event}")



async def monitor_single_match(self, match_info: Dict):
        """监控单场比赛"""
        match_id = match_info['id']
        page = None
        
        try:
            page = await self.context.new_page()
            self.monitoring_pages[match_id] = page
            
            print(f"[{match_id}] 启动监控: {match_info['home']} vs {match_info['away']}")
            
            await page.goto(match_info['url'], wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)
            
            # 尝试点击进入动画直播
            clicked = False
            for text in ['动画直播', '直播数据', '动画', '技术统计']:
                try:
                    await page.click(f'text={text}', timeout=5000)
                    await asyncio.sleep(3)
                    clicked = True
                    print(f"[{match_id}] 已进入 {text}")
                    break
                except:
                    continue
            
            # 更新队伍信息（DOM方式）
            dom_info = await self.extract_team_names_and_score_dom(page)
            for key in ['home', 'away', 'score', 'status']:
                if dom_info.get(key):
                    match_info[key] = dom_info[key]
            
            # 检查是否有事件区域
            if not await self.check_target_element_exists(page):
                print(f"[{match_id}] 无事件区域，{self.close_delay}s后关闭")
                await asyncio.sleep(self.close_delay)
                return
            
            # 初始化数据结构
            if match_id not in self.corner_data:
                self.corner_data[match_id] = {'match_info': match_info.copy(), 'events': []}
            if match_id not in self.corner_only_data:
                self.corner_only_data[match_id] = {'match_info': match_info.copy(), 'corners': []}
            
            last_update = 0
            zero_score_time = None
            
            while True:
                try:
                    # 更新比分和状态
                    dom_info = await self.extract_team_names_and_score_dom(page)
                    for key in ['home', 'away', 'score', 'status']:
                        if dom_info.get(key):
                            self.corner_data[match_id]['match_info'][key] = dom_info[key]
                            self.corner_only_data[match_id]['match_info'][key] = dom_info[key]
                    
                    # 0:0 检测
                    current_score = dom_info.get('score', '') or match_info['score']
                    if current_score.replace('：', ':') in ['0:0', '0：0']:
                        if zero_score_time is None:
                            zero_score_time = asyncio.get_event_loop().time()
                        elapsed = asyncio.get_event_loop().time() - zero_score_time
                        if elapsed > self.close_delay:
                            print(f"[{match_id}] 0:0 超时，关闭监控")
                            break
                    else:
                        zero_score_time = None
                    
                    # DOM方式提取事件
                    all_events = await self.extract_all_events_dom(page)
                    corner_events = await self.extract_corner_events_dom(page)
                    
                    # 更新事件（去重）
                    existing_all = self.corner_data[match_id]['events']
                    new_all = [e for e in all_events if e not in existing_all]
                    existing_all.extend(new_all)
                    
                    existing_corners = self.corner_only_data[match_id]['corners']
                    new_corners = [c for c in corner_events if c not in existing_corners]
                    existing_corners.extend(new_corners)
                    
                    # 有新角球时保存
                    if new_corners:
                        self.save_corner_data()
                        print(f"[{match_id}] 新增 {len(new_corners)} 个角球")
                    
                    # 定期刷新表格
                    now = asyncio.get_event_loop().time()
                    if new_all or new_corners or (now - last_update > 10):
                        self.print_live_table()
                        last_update = now
                    
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"[{match_id}] 监控循环异常: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            print(f"[{match_id}] 启动失败: {e}")
        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                except:
                    pass
            if match_id in self.monitoring_pages:
                del self.monitoring_pages[match_id]



async def periodic_refresh(self):
        """定期扫描新比赛"""
        while True:
            await asyncio.sleep(self.refresh_interval)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 定期扫描新比赛...")
            new_matches = await self.get_live_matches()
            
            current_ids = set(self.monitoring_pages.keys())
            new_ids = {m['id'] for m in new_matches}
            
            # 关闭已结束的
            for old_id in current_ids - new_ids:
                if old_id in self.monitoring_pages:
                    page = self.monitoring_pages[old_id]
                    await page.close()
                    del self.monitoring_pages[old_id]
                    print(f"[{old_id}] 比赛结束，关闭")
            
            # 添加新的
            to_add = [m for m in new_matches if m['id'] not in current_ids]
            if to_add:
                print(f"发现 {len(to_add)} 场新比赛")
                for m in to_add:
                    asyncio.create_task(self.monitor_single_match(m))
            
            self.save_corner_data()
            self.print_live_table()
  
    async def periodic_save(self):
        """每10秒保存一次角球数据"""
        while True:
            await asyncio.sleep(10)
            self.save_corner_data()
  
    async def start_monitoring(self):
        """主监控入口"""
        print("="*130)
        print("足球角球监控系统 v3.0 (DOM解析版 - 无头模式)".center(130))  # 🔴 添加无头模式标识
        print("="*130)
        
        await self.init_browser(headless=True)  # 🔴 确保使用无头模式
        
        try:
            matches = await self.get_live_matches()
            print(f"初始发现 {len(matches)} 场比赛")
            
            tasks = []
            for m in matches:
                tasks.append(asyncio.create_task(self.monitor_single_match(m)))
            
            tasks.append(asyncio.create_task(self.periodic_refresh()))
            tasks.append(asyncio.create_task(self.periodic_save()))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            print(f"主程序异常: {e}")
        finally:
            self.print_live_table()
            self.save_corner_data()
            await self.close_browser()

async def main():
    scraper = CornerKickScraper()
    try:
        await scraper.start_monitoring()
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    finally:
        print("程序结束")

if __name__ == "__main__":
    print("\n" + "="*130)
    print("足球角球DOM监控系统启动 (无头模式)".center(130))  # 🔴 添加无头模式标识
    print("特性：无头浏览器后台运行 | DOM精确解析角球事件 | 自动进入动画直播 | 实时表格显示 | 智能关闭无用页面".center(130))
    print("="*130)
    asyncio.run(main())


