import asyncio
from playwright.async_api import async_playwright, Page
from datetime import datetime
import json
from typing import List, Dict
import os

class CornerKickScraper:
    def __init__(self):
        self.base_url = "https://www.599.com"
        self.corner_data = {}
        self.corner_only_data = {}
        self.corner_file = 'corner_only_data.json'
        self.browser = None
        self.context = None
        self.monitoring_pages = {}
        self.refresh_interval = 300
        self.close_delay = 200
       
    async def init_browser(self, headless=False):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
       
    async def close_browser(self):
        """关闭浏览器"""
        for page in self.monitoring_pages.values():
            try:
                await page.close()
            except:
                pass
       
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
async def get_live_matches(self) -> List[Dict]:
        """获取所有进行中的比赛(排除未开)"""
        page = await self.context.new_page()
       
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在扫描比赛列表...")
            await page.goto(f"{self.base_url}/live/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
           
            matches = []
           
            matches_data = await page.evaluate('''() => {
                const results = [];
               
                let rows = document.querySelectorAll('.match');
                if (rows.length === 0) {
                    rows = document.querySelectorAll('tr[data-mid]');
                }
                if (rows.length === 0) {
                    rows = document.querySelectorAll('table tr');
                }
               
                rows.forEach((row, index) => {
                    try {
                        const tds = row.querySelectorAll('td');
                        if (tds.length < 5) return;
                       
                        let status = '';
                        let home = '';
                        let score = '';
                        let away = '';
                        let href = '';
                       
                        const statusPatterns = ['上半场', '下半场', '中场', '未开', '完场', '加时', '点球'];
                        const timePattern = /^\\d+\\s*['′']\\s*$/;
                        const scorePattern = /^\\d+\\s*[: ：]\\s*\\d+$/;
                       
                        for (let i = 0; i < tds.length; i++) {
                            const text = tds[i].innerText.trim();
                           
                            if (statusPatterns.some(p => text.includes(p)) || timePattern.test(text)) {
                                status = text;
                            }
                            else if (scorePattern.test(text.replace(/\\s/g, ''))) {
                                score = text;
                            }
                        }
                       
                        const links = row.querySelectorAll('a[href*="/live/"]');
                        for (const link of links) {
                            const h = link.getAttribute('href');
                            if (h && h.includes('/live/') && !h.includes('odds')) {
                                href = h;
                                const linkText = link.innerText.trim();
                                if (linkText && linkText.length > 1 && !scorePattern.test(linkText)) {
                                    if (!home) {
                                        home = linkText;
                                    } else if (!away && linkText !== home) {
                                        away = linkText;
                                    }
                                }
                            }
                        }
                       
                        if (!home || !away) {
                            for (let i = 0; i < tds.length; i++) {
                                const text = tds[i].innerText.trim();
                                if (text.length > 1 &&
                                    !statusPatterns.some(p => text.includes(p)) &&
                                    !timePattern.test(text) &&
                                    !scorePattern.test(text.replace(/\\s/g, '')) &&
                                    !/^\\d{1,2}:\\d{2}$/.test(text) &&
                                    text !== 'VS') {
                                    if (!home) {
                                        home = text;
                                    } else if (!away && text !== home) {
                                        away = text;
                                    }
                                }
                            }
                        }
                       
                        if (href) {
                            results.push({
                                index: index,
                                status: status,
                                home: home,
                                away: away,
                                score: score,
                                href: href,
                                rowText: row.innerText.substring(0, 200)
                            });
                        }
                    } catch (e) {
                        console.log('解析行出错:', e);
                    }
                });
               
                return results;
            }''')
           
            print(f"页面共找到 {len(matches_data)} 场比赛")
           
            for data in matches_data:
                if '未开' in data['status'] or data['status'] == '' or 'VS' in data.get('rowText', ''):
                    if '未开' in data.get('rowText', '') or (not data['status'] and 'VS' in data.get('rowText', '')):
                        continue
               
                if not data['href']:
                    continue
               
                match_url = f"{self.base_url}{data['href']}" if data['href'].startswith('/') else data['href']
                match_id = data['href'].split('/')[-2] if '/' in data['href'] else f"match_{len(matches)}"
               
                match_info = {
                    'id': match_id,
                    'url': match_url,
                    'home': data['home'] if data['home'] else '未知主队',
                    'away': data['away'] if data['away'] else '未知客队',
                    'score': data['score'] if data['score'] else '0:0',
                    'status': data['status'] if data['status'] else '进行中'
                }
               
                matches.append(match_info)
                print(f"✓ [{match_id}] {match_info['home']} vs {match_info['away']} ({match_info['status']}) {match_info['score']}")
           
            await page.close()
            return matches
           
        except Exception as e:
            print(f"获取比赛列表出错: {str(e)}")
            import traceback
            traceback.print_exc()
            await page.close()
            return []

async def check_target_element_exists(self, page: Page) -> bool:
        """检查目标元素是否存在(动画直播区域)"""
        try:
            await asyncio.sleep(2)
           
            # ⭐ 关键修复：检查是否有角球图标元素
            has_corner_elements = await page.evaluate('''() => {
                // 检查是否有角球相关的img元素
                const cornerImgs = document.querySelectorAll('img.corner_tips, img[class*="corner"]');
                if (cornerImgs.length > 0) return true;
                
                // 检查是否有事件列表容器
                const eventContainers = document.querySelectorAll(
                    'div.live_main, div.data_chart, div[class*="event"], div[class*="live"]'
                );
                if (eventContainers.length > 0) return true;
                
                const pageText = document.body.innerText;
                if (pageText.includes('主队') && pageText.includes('客队')) return true;
                if (pageText.includes('角球') || pageText.includes('获得角球')) return true;
                if (pageText.includes('上半场') || pageText.includes('下半场')) return true;
                
                return false;
            }''')
           
            return has_corner_elements
           
        except Exception as e:
            return False
   
    async def extract_corner_events(self, page: Page) -> List[str]:
        """⭐ 核心修复：从img标签的title属性提取角球事件"""
        try:
            corner_events = await page.evaluate('''() => {
                const corners = [];
                const processedTexts = new Set();
                
                // ⭐ 方法1：从img.corner_tips的title属性提取
                const cornerImgs = document.querySelectorAll('img.corner_tips, img[class*="corner"]');
                cornerImgs.forEach(img => {
                    const title = img.getAttribute('title');
                    if (title && title.includes('角球')) {
                        // 获取时间信息
                        let timeText = '';
                        
                        // 尝试从父元素或兄弟元素中找时间
                        let parent = img.closest('div');
                        if (parent) {
                            const parentText = parent.innerText;
                            const timeMatch = parentText.match(/(\\d+)['′']/);
                            if (timeMatch) {
                                timeText = timeMatch[0] + ' ';
                            }
                        }
                        
                        const fullText = timeText + title;
                        if (!processedTexts.has(fullText)) {
                            corners.push(fullText);
                            processedTexts.add(fullText);
                        }
                    }
                });
                
                // ⭐ 方法2：从data-v属性的img中提取（您截图中的格式）
                const dataVImgs = document.querySelectorAll('img[data-v-4ac70cac]');
                dataVImgs.forEach(img => {
                    const title = img.getAttribute('title');
                    if (title && (title.includes('角球') || title.includes('获得角球'))) {
                        let timeText = '';
                        
                        // 查找同级或父级元素中的时间
                        const container = img.closest('div');
                        if (container) {
                            const allText = container.innerText;
                            const lines = allText.split('\\n');
                            for (const line of lines) {
                                if (/^\\d+['′']$/.test(line.trim())) {
                                    timeText = line.trim() + ' ';
                                    break;
                                }
                            }
                        }
                        
                        const fullText = timeText + title;
                        if (!processedTexts.has(fullText)) {
                            corners.push(fullText);
                            processedTexts.add(fullText);
                        }
                    }
                });
                
                // ⭐ 方法3：从页面文本中提取（备用方案）
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                let prevTime = '';
                for (let i = 0; i < lines.length; i++) {
                    const text = lines[i].trim();
                    
                    if (/^\\d+['′']$/.test(text)) {
                        prevTime = text;
                        continue;
                    }
                    
                    if (text.includes('角球') && text.includes('获得')) {
                        let fullText = '';
                        if (prevTime) {
                            fullText = prevTime + ' ' + text;
                        } else if (/^\\d+['′']/.test(text)) {
                            fullText = text;
                        } else {
                            fullText = text;
                        }
                        
                        if (fullText && !processedTexts.has(fullText) && fullText.length < 100) {
                            corners.push(fullText);
                            processedTexts.add(fullText);
                        }
                        prevTime = '';
                    }
                }
                
                return corners;
            }''')
           
            return corner_events
           
        except Exception as e:
            print(f"提取角球事件失败: {str(e)}")
            return []
   
    async def extract_all_event_text(self, page: Page) -> List[str]:
        """⭐ 修复：提取所有事件（包括从img title中提取）"""
        try:
            all_events = await page.evaluate('''() => {
                const events = [];
                const processedTexts = new Set();
                
                // ⭐ 方法1：从所有img的title属性提取事件
                const eventImgs = document.querySelectorAll('img[title]');
                eventImgs.forEach(img => {
                    const title = img.getAttribute('title');
                    if (title && title.length > 3 && title.length < 100) {
                        // 尝试找到时间信息
                        let timeText = '';
                        const container = img.closest('div');
                        if (container) {
                            const containerText = container.innerText;
                            const timeMatch = containerText.match(/(\\d+)['′']/);
                            if (timeMatch) {
                                timeText = timeMatch[0] + ' ';
                            }
                        }
                        
                        const fullText = timeText + title;
                        if (!processedTexts.has(fullText)) {
                            events.push(fullText);
                            processedTexts.add(fullText);
                        }
                    }
                });
                
                // ⭐ 方法2：从页面文本提取
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n');
                
                let prevTime = '';
                for (let i = 0; i < lines.length; i++) {
                    const text = lines[i].trim();
                    
                    if (/^\\d+['′']$/.test(text)) {
                        prevTime = text;
                        continue;
                    }
                    
                    if (prevTime && text.length > 3 && text.length < 100) {
                        if (!text.includes('射门') || text.includes('球')) {
                            const combined = prevTime + ' ' + text;
                            if (!processedTexts.has(combined)) {
                                events.push(combined);
                                processedTexts.add(combined);
                            }
                        }
                        prevTime = '';
                    }
                    else if (/^\\d+['′']/.test(text) && text.length > 5 && text.length < 150) {
                        if (!processedTexts.has(text)) {
                            events.push(text);
                            processedTexts.add(text);
                        }
                        prevTime = '';
                    }
                }
                
                return events;
            }''')
           
            return all_events
           
        except Exception as e:
            print(f"提取所有事件失败: {str(e)}")
            return []

async def extract_team_names_from_animation(self, page: Page) -> Dict:
        """从动画直播区域提取主客队名字"""
        try:
            team_info = await page.evaluate('''() => {
                let home = '';
                let away = '';
                let score = '';
                let status = '';
               
                const allElements = document.querySelectorAll('*');
               
                for (const elem of allElements) {
                    const text = elem.innerText || '';
                   
                    if (text.includes('主队') && text.length < 200) {
                        const parent = elem.closest('div');
                        if (parent) {
                            const parentText = parent.innerText;
                            const lines = parentText.split('\n');
                            for (const line of lines) {
                                const trimmed = line.trim();
                                if (trimmed && trimmed.length > 1 && trimmed.length < 30 &&
                                    !trimmed.includes('主队') && !trimmed.includes('客队') &&
                                    !/^\\d+\\s*[: ：]\\s*\\d+$/.test(trimmed) &&
                                    !/^\\d+['′']$/.test(trimmed)) {
                                    if (!home) home = trimmed;
                                }
                            }
                        }
                    }
                }
               
                const animationContainer = document.querySelector('[class*="animation"], [class*="live"], [class*="match"]');
                if (animationContainer) {
                    const containerText = animationContainer.innerText;
                    const lines = containerText.split('\n').map(l => l.trim()).filter(l => l);
                   
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i];
                        if (/^\\d+\\s*[:：]\\s*\\d+$/.test(line.replace(/\\s/g, ''))) {
                            score = line;
                            if (i > 0 && lines[i-1].length > 1 && lines[i-1].length < 30) {
                                if (!home) home = lines[i-1];
                            }
                            if (i < lines.length - 1 && lines[i+1].length > 1 && lines[i+1].length < 30) {
                                if (!away) away = lines[i+1];
                            }
                        }
                    }
                }
               
                const homeElements = document.querySelectorAll('[class*="home"], [class*="left"], [class*="主队"]');
                const awayElements = document.querySelectorAll('[class*="away"], [class*="right"], [class*="客队"]');
               
                for (const elem of homeElements) {
                    const text = elem.innerText.trim();
                    if (text && text.length > 1 && text.length < 30 &&
                        !text.includes('主队') && !/\\d+[: ：]\\d+/.test(text)) {
                        if (!home) home = text.split('\n')[0].trim();
                    }
                }
               
                for (const elem of awayElements) {
                    const text = elem.innerText.trim();
                    if (text && text.length > 1 && text.length < 30 &&
                        !text.includes('客队') && !/\\d+[:：]\\d+/.test(text)) {
                        if (!away) away = text.split('\n')[0].trim();
                    }
                }
               
                const bodyText = document.body.innerText;
                const scoreMatch = bodyText.match(/(\\d+)\\s*[:：]\\s*(\\d+)/);
                if (scoreMatch && !score) {
                    score = scoreMatch[0];
                }
               
                const timeMatch = bodyText.match(/(\\d+)['′']/);
                if (timeMatch) {
                    status = timeMatch[0];
                }
               
                if (bodyText.includes('中场')) status = '中场';
                if (bodyText.includes('上半场')) status = '上半场';
                if (bodyText.includes('下半场')) status = '下半场';
               
                return { home, away, score, status };
            }''')
           
            return team_info
           
        except Exception as e:
            return {'home': '', 'away': '', 'score': '', 'status': ''}
   
    async def get_match_info_from_page(self, page: Page) -> Dict:
        """从比赛详情页获取完整的比赛信息"""
        try:
            match_info = await page.evaluate('''() => {
                let home = '';
                let away = '';
                let score = '';
                let status = '';
               
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\n').map(l => l.trim()).filter(l => l);
               
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                   
                    const scoreMatch = line.match(/^(\\d+)\\s*[:：]\\s*(\\d+)$/);
                    if (scoreMatch) {
                        score = line;
                        for (let j = i - 1; j >= 0 && j >= i - 5; j--) {
                            const prevLine = lines[j];
                            if (prevLine.length > 1 && prevLine.length < 30 &&
                                !prevLine.includes('主队') && !prevLine.includes('客队') &&
                                !/^\\d+['′']/.test(prevLine) && !/^\\d+:\\d+$/.test(prevLine) &&
                                !prevLine.includes('HT') && !prevLine.includes('动画')) {
                                if (!home) home = prevLine;
                                break;
                            }
                        }
                        for (let j = i + 1; j < lines.length && j <= i + 5; j++) {
                            const nextLine = lines[j];
                            if (nextLine.length > 1 && nextLine.length < 30 &&
                                !nextLine.includes('主队') && !nextLine.includes('客队') &&
                                !/^\\d+['′']/.test(nextLine) && !/^\\d+:\\d+$/.test(nextLine) &&
                                !nextLine.includes('HT') && !nextLine.includes('动画') &&
                                nextLine !== home) {
                                if (!away) away = nextLine;
                                break;
                            }
                        }
                    }
                }
               
                if (!home || !away) {
                    const teamElements = document.querySelectorAll('[class*="team"], [class*="name"]');
                    const teamNames = [];
                   
                    for (const elem of teamElements) {
                        const text = elem.innerText.trim();
                        if (text && text.length > 1 && text.length < 30 &&
                            !text.includes('主队') && !text.includes('客队') &&
                            !/\\d+[:：]\\d+/.test(text) && !/^\\d+['′']$/.test(text)) {
                            const firstLine = text.split('\n')[0].trim();
                            if (firstLine && !teamNames.includes(firstLine)) {
                                teamNames.push(firstLine);
                            }
                        }
                    }
                   
                    if (teamNames.length >= 2) {
                        if (!home) home = teamNames[0];
                        if (!away) away = teamNames[1];
                    }
                }
               
                for (const line of lines) {
                    if (/^\\d+['′']$/.test(line)) {
                        status = line;
                        break;
                    }
                }
               
                if (bodyText.includes('中场') && !status) status = '中场';
                if (bodyText.includes('上半场的比赛结束')) status = '中场';
               
                return { home, away, score, status };
            }''')
           
            return match_info
           
        except Exception as e:
            return {'home': '', 'away': '', 'score': '', 'status': ''}
   
    async def check_animation_score(self, page: Page) -> str:
        """检查动画直播中的比分"""
        try:
            score = await page.evaluate('''() => {
                const scorePattern = /(\\d+)\\s*[:：]\\s*(\\d+)/;
               
                const scoreElements = document.querySelectorAll('[class*="score"], [class*="Score"]');
                for (const elem of scoreElements) {
                    const text = elem.innerText;
                    const match = text.match(scorePattern);
                    if (match) {
                        return match[1] + ':' + match[2];
                    }
                }
               
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\n');
                for (const line of lines) {
                    const text = line.trim();
                    if (text.length < 10) {
                        const match = text.match(scorePattern);
                        if (match) {
                            return match[1] + ':' + match[2];
                        }
                    }
                }
               
                return '';
            }''')
           
            return score if score else ''
           
        except Exception as e:
            return ''

def save_corner_data(self):
        """保存角球数据到JSON文件（覆盖式更新）"""
        try:
            output_data = {
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_matches': len(self.corner_only_data),
                'matches': {}
            }
           
            total_corners = 0
            for match_id, data in self.corner_only_data.items():
                match_corners = data.get('corners', [])
               
                home_corners = len([c for c in match_corners if '主队' in c and '角球' in c])
                away_corners = len([c for c in match_corners if '客队' in c and '角球' in c])
               
                output_data['matches'][match_id] = {
                    'match_info': {
                        'home': data['match_info']['home'],
                        'away': data['match_info']['away'],
                        'score': data['match_info']['score'],
                        'status': data['match_info']['status']
                    },
                    'corner_stats': {
                        'total': len(match_corners),
                        'home': home_corners,
                        'away': away_corners
                    },
                    'corner_events': match_corners
                }
                total_corners += len(match_corners)
           
            output_data['total_corners'] = total_corners
           
            with open(self.corner_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
           
        except Exception as e:
            print(f"保存角球数据失败: {str(e)}")
   
    def print_live_table(self):
        """实时打印角球统计表格"""
        os.system('cls' if os.name == 'nt' else 'clear')
       
        print("\n" + "="*120)
        print("足球角球实时监控 - 数据总览".center(120))
        print("="*120)
        print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"监控中的比赛: {len(self.monitoring_pages)} 场")
        print(f"角球数据文件: {self.corner_file} (实时更新)")
        print("="*120)
       
        if not self.corner_data:
            print("暂无角球数据".center(120))
            print("="*120)
            return
       
        header = f"{'比赛ID':<15} {'主队':<20} {'客队':<20} {'比分':<10} {'状态':<10} {'事件数':<8} {'角球数':<8}"
        print(header)
        print("-"*120)
       
        total_events = 0
        total_corners = 0
        for match_id, data in sorted(self.corner_data.items()):
            info = data['match_info']
            events = data['events']
            event_count = len(events)
            total_events += event_count
           
            corner_count = 0
            if match_id in self.corner_only_data:
                corner_count = len(self.corner_only_data[match_id].get('corners', []))
            total_corners += corner_count
           
            home = info['home'][:18] if len(info['home']) > 18 else info['home']
            away = info['away'][:18] if len(info['away']) > 18 else info['away']
           
            row = f"{match_id:<15} {home:<20} {away:<20} {info['score']:<10} {info['status']:<10} {event_count:<8} {corner_count:<8}"
            print(row)
       
        print("-"*120)
        print(f"总计: {len(self.corner_data)} 场比赛, {total_events} 个事件, {total_corners} 个角球")
        print("="*120)
       
        if total_corners > 0:
            print("\n⚽ 角球详细信息:")
            print("="*120)
           
            for match_id, data in sorted(self.corner_only_data.items()):
                corners = data.get('corners', [])
                if corners:
                    info = data['match_info']
                    home_count = len([c for c in corners if '主队' in c])
                    away_count = len([c for c in corners if '客队' in c])
                   
                    print(f"\n🏆 {info['home']} vs {info['away']} ({info['status']}) {info['score']}")
                    print(f" 角球统计: 主队 {home_count} - 客队 {away_count}")
                    print("-"*120)
                    for i, corner in enumerate(corners, 1):
                        print(f" {i}. {corner}")
       
        if total_events > 0:
            print("\n📍 所有事件详细信息:")
            print("="*120)
           
            for match_id, data in sorted(self.corner_data.items()):
                info = data['match_info']
                events = data['events']
               
                if events:
                    print(f"\n🏆 {info['home']} vs {info['away']} ({info['status']}) {info['score']}")
                    print("-"*120)
                    for i, event in enumerate(events, 1):
                        print(f" {i}. {event}")
       
        print("\n" + "="*120)
        print(f"每5分钟自动扫描新比赛 | 比分0:0在{self.close_delay}秒后关闭 | 无事件元素自动关闭 | 按 Ctrl+C 停止监控")
        print("="*120)



async def monitor_single_match(self, match_info: Dict):
        """监控单场比赛的角球数据"""
        match_id = match_info['id']
        page = None
       
        try:
            page = await self.context.new_page()
            self.monitoring_pages[match_id] = page
           
            print(f"[{match_id}] 🚀 启动监控: {match_info['home']} vs {match_info['away']}")
           
            await page.goto(match_info['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
           
            # 尝试点击动画直播按钮
            animation_selectors = [
                'text=动画直播',
                'text=直播数据',
                'a:has-text("动画直播")',
                'a:has-text("直播数据")'
            ]
           
            animation_clicked = False
            for selector in animation_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(3)
                        animation_clicked = True
                        print(f"[{match_id}] ✓ 进入动画直播/直播数据")
                        break
                except:
                    continue
           
            if not animation_clicked:
                print(f"[{match_id}] ⚠ 未找到动画直播按钮，尝试直接获取数据")
           
            # 获取比赛信息
            page_match_info = await self.get_match_info_from_page(page)
           
            if page_match_info['home']:
                match_info['home'] = page_match_info['home']
            if page_match_info['away']:
                match_info['away'] = page_match_info['away']
            if page_match_info['score']:
                match_info['score'] = page_match_info['score']
            if page_match_info['status']:
                match_info['status'] = page_match_info['status']
           
            print(f"[{match_id}] 📋 球队信息: {match_info['home']} vs {match_info['away']} ({match_info['status']}) {match_info['score']}")
           
            # ⭐ 检查是否有事件元素（使用修复后的函数）
            has_target_element = await self.check_target_element_exists(page)
           
            if not has_target_element:
                print(f"[{match_id}] ❌ 页面没有事件列表元素,将在{self.close_delay}秒后关闭此页面")
                await asyncio.sleep(self.close_delay)
                await page.close()
                if match_id in self.monitoring_pages:
                    del self.monitoring_pages[match_id]
                return
           
            print(f"[{match_id}] ✓ 找到事件列表元素,开始监控")
           
            # 初始化数据结构
            if match_id not in self.corner_data:
                self.corner_data[match_id] = {
                    'match_info': match_info.copy(),
                    'events': []
                }
           
            if match_id not in self.corner_only_data:
                self.corner_only_data[match_id] = {
                    'match_info': match_info.copy(),
                    'corners': []
                }
           
            last_table_update = 0
            zero_score_start_time = None
           
            # 主监控循环
            while True:
                try:
                    # 更新比赛信息
                    page_match_info = await self.get_match_info_from_page(page)
                   
                    if page_match_info['home']:
                        self.corner_data[match_id]['match_info']['home'] = page_match_info['home']
                        self.corner_only_data[match_id]['match_info']['home'] = page_match_info['home']
                    if page_match_info['away']:
                        self.corner_data[match_id]['match_info']['away'] = page_match_info['away']
                        self.corner_only_data[match_id]['match_info']['away'] = page_match_info['away']
                    if page_match_info['score']:
                        self.corner_data[match_id]['match_info']['score'] = page_match_info['score']
                        self.corner_only_data[match_id]['match_info']['score'] = page_match_info['score']
                    if page_match_info['status']:
                        self.corner_data[match_id]['match_info']['status'] = page_match_info['status']
                        self.corner_only_data[match_id]['match_info']['status'] = page_match_info['status']
                   
                    animation_score = page_match_info['score'] if page_match_info['score'] else await self.check_animation_score(page)
                   
                    # 0:0 自动关闭逻辑
                    if animation_score in ['0:0', '0：0']:
                        if zero_score_start_time is None:
                            zero_score_start_time = asyncio.get_event_loop().time()
                            print(f"[{match_id}] ⚠ 检测到比分 {animation_score}, 开始{self.close_delay}秒倒计时")
                       
                        elapsed = asyncio.get_event_loop().time() - zero_score_start_time
                        remaining = self.close_delay - elapsed
                       
                        if remaining <= 0:
                            print(f"[{match_id}] 🔴 比分为 0:0 超过{self.close_delay}秒,关闭监控")
                            break
                        elif int(elapsed) % 30 == 0 and int(elapsed) > 0:
                            print(f"[{match_id}] ⏱ 比分0:0, 还剩 {int(remaining)} 秒关闭")
                    else:
                        if zero_score_start_time is not None and animation_score:
                            print(f"[{match_id}] ✓ 比分更新为 {animation_score}, 取消关闭倒计时")
                        zero_score_start_time = None
                   
                    # ⭐ 使用修复后的提取函数
                    all_events = await self.extract_all_event_text(page)
                    corner_events = await self.extract_corner_events(page)
                   
                    # 更新事件数据
                    new_events = 0
                    for event in all_events:
                        if event not in self.corner_data[match_id]['events']:
                            self.corner_data[match_id]['events'].append(event)
                            new_events += 1
                   
                    # 更新角球数据
                    new_corners = 0
                    existing_corners = self.corner_only_data[match_id]['corners']
                    for corner in corner_events:
                        if corner not in existing_corners:
                            existing_corners.append(corner)
                            new_corners += 1
                   
                    if new_corners > 0:
                        self.save_corner_data()
                        print(f"[{match_id}] ⚽ 新增 {new_corners} 个角球事件，已更新 {self.corner_file}")
                   
                    # 更新显示
                    current_time = asyncio.get_event_loop().time()
                    if new_events > 0 or new_corners > 0 or (current_time - last_table_update > 10):
                        self.print_live_table()
                        last_table_update = current_time
                   
                    await asyncio.sleep(3)
                   
                except Exception as e:
                    await asyncio.sleep(3)
                   
        except Exception as e:
            print(f"[{match_id}] ❌ 监控失败: {str(e)}")
        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                    print(f"[{match_id}] 📴 已关闭标签页")
                except:
                    pass
           
            if match_id in self.monitoring_pages:
                del self.monitoring_pages[match_id]

async def periodic_refresh(self):
        """定期刷新比赛列表"""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
               
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏰ 开始定期扫描新比赛...")
               
                new_matches = await self.get_live_matches()
               
                existing_ids = set(self.monitoring_pages.keys())
                new_match_ids = {m['id'] for m in new_matches}
               
                to_add = [m for m in new_matches if m['id'] not in existing_ids]
                to_remove = existing_ids - new_match_ids
               
                for match_id in to_remove:
                    if match_id in self.monitoring_pages:
                        page = self.monitoring_pages[match_id]
                        try:
                            await page.close()
                            print(f"[{match_id}] 🔴 比赛已结束,关闭监控")
                        except:
                            pass
                        del self.monitoring_pages[match_id]
               
                if to_add:
                    print(f"发现 {len(to_add)} 场新比赛,启动监控...")
                    for match in to_add:
                        asyncio.create_task(self.monitor_single_match(match))
                else:
                    print("没有发现新比赛")
               
                self.save_corner_data()
                self.print_live_table()
               
            except Exception as e:
                print(f"定期刷新出错: {str(e)}")
   
    async def periodic_save_corner_data(self):
        """定期保存角球数据（每10秒）"""
        while True:
            try:
                await asyncio.sleep(10)
                self.save_corner_data()
            except Exception as e:
                pass
   
    async def start_monitoring(self):
        """启动监控"""
        print("="*120)
        print("足球角球数据爬虫 - 开始运行".center(120))
        print("="*120)
       
        await self.init_browser(headless=False)
       
        try:
            matches = await self.get_live_matches()
           
            if not matches:
                print("\n⚠ 当前没有进行中的比赛(已排除状态为'未开'的比赛)")
                print(f"将在 {self.refresh_interval} 秒后重新扫描...")
            else:
                print(f"\n找到 {len(matches)} 场需要监控的比赛")
           
            print("="*120)
            print(f"监控规则:")
            print(f" - 只监控状态不是'未开'的比赛")
            print(f" - 每3秒检测事件数据和比分")
            print(f" - ⭐ 从img标签的title属性提取角球事件")
            print(f" - 页面没有事件列表元素则在{self.close_delay}秒后关闭")
            print(f" - 比分为0:0持续{self.close_delay}秒则自动关闭标签页")
            print(f" - 每{self.refresh_interval}秒扫描新比赛")
            print(f" - 自动关闭已结束比赛的标签页")
            print(f" - 角球数据实时保存到: {self.corner_file}")
            print("="*120)
           
            tasks = []
            for match in matches:
                task = asyncio.create_task(self.monitor_single_match(match))
                tasks.append(task)
           
            refresh_task = asyncio.create_task(self.periodic_refresh())
            tasks.append(refresh_task)
           
            save_corner_task = asyncio.create_task(self.periodic_save_corner_data())
            tasks.append(save_corner_task)
           
            await asyncio.gather(*tasks, return_exceptions=True)
           
        except Exception as e:
            print(f"\n监控过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
   
    def save_data(self, filename='match_events_data.json'):
        """保存数据到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.corner_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 所有事件数据已保存到: {filename}")
        except Exception as e:
            print(f"\n✗ 保存数据失败: {str(e)}")
   
    def print_final_summary(self):
        """打印最终统计摘要"""
        print("\n" + "="*120)
        print("最终统计摘要".center(120))
        print("="*120)
       
        if not self.corner_data:
            print("没有收集到事件数据".center(120))
            print("="*120)
            return
       
        header = f"{'比赛ID':<15} {'主队':<20} {'客队':<20} {'比分':<10} {'状态':<10} {'事件数':<8} {'角球数':<8}"
        print(header)
        print("-"*120)
       
        total_events = 0
        total_corners = 0
        for match_id, data in sorted(self.corner_data.items()):
            info = data['match_info']
            events = data['events']
            event_count = len(events)
            total_events += event_count
           
            corner_count = 0
            if match_id in self.corner_only_data:
                corner_count = len(self.corner_only_data[match_id].get('corners', []))
            total_corners += corner_count
           
            home = info['home'][:18] if len(info['home']) > 18 else info['home']
            away = info['away'][:18] if len(info['away']) > 18 else info['away']
           
            row = f"{match_id:<15} {home:<20} {away:<20} {info['score']:<10} {info['status']:<10} {event_count:<8} {corner_count:<8}"
            print(row)
       
        print("-"*120)
        print(f"总计: {len(self.corner_data)} 场比赛, {total_events} 个事件, {total_corners} 个角球")
        print("="*120)
       
        if total_corners > 0:
            print("\n⚽ 角球详细记录:")
            print("="*120)
           
            for match_id, data in sorted(self.corner_only_data.items()):
                corners = data.get('corners', [])
                if corners:
                    info = data['match_info']
                    home_count = len([c for c in corners if '主队' in c])
                    away_count = len([c for c in corners if '客队' in c])
                   
                    print(f"\n🏆 [{match_id}] {info['home']} vs {info['away']}")
                    print(f" 状态: {info['status']} | 比分: {info['score']}")
                    print(f" 角球统计: 主队 {home_count} - 客队 {away_count} (总计: {len(corners)})")
                    print(" 角球详情:")
                    for i, corner in enumerate(corners, 1):
                        print(f" {i}. {corner}")
       
        print("\n" + "="*120)

async def main():
    """主函数"""
    scraper = CornerKickScraper()
   
    try:
        await scraper.start_monitoring()
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断,正在保存数据...")
    except Exception as e:
        print(f"\n程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.print_final_summary()
        scraper.save_data()
        scraper.save_corner_data()
       
        print("\n准备关闭浏览器...")
        await asyncio.sleep(2)
        await scraper.close_browser()

if __name__ == "__main__":
    print("\n" + "="*120)
    print("足球比赛事件实时监控系统 v2.8 (修复版)".center(120))
    print("="*120)
    print("功能特性:".center(120))
    print("✓ 自动识别进行中的比赛(严格排除'未开'状态)".center(120))
    print("✓ ⭐ 从img标签的title属性提取角球事件(已修复)".center(120))
    print("✓ 实时监控所有比赛事件(角球、进球、换人等),3秒刷新".center(120))
    print("✓ 智能检测事件列表元素,无元素200秒后关闭页面".center(120))
    print("✓ 比分为0:0持续200秒自动关闭标签页".center(120))
    print("✓ 每5分钟自动扫描新比赛".center(120))
    print("✓ 实时表格显示,事件与比赛关联".center(120))
    print("="*120)
    print("按 Ctrl+C 停止监控并保存数据\n".center(120))
   
    asyncio.run(main())
