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
        self.corner_data = {}
        self.corner_only_data = {}
        self.corner_file = 'corner_only_data.json'
        self.browser = None
        self.context = None
        self.monitoring_pages = {}
        self.refresh_interval = 300
        self.close_delay = 200

    async def init_browser(self, headless=True):
        """初始化浏览器（添加反检测参数）"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
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
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        """)
        print("✓ 浏览器已启动（无头模式）")

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
            await asyncio.sleep(4)

            matches_data = await page.evaluate('''() => {
                const results = [];
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

                        for (let i = 0; i < tds.length; i++) {
                            const text = tds[i].innerText.trim();
                            if (statusPatterns.some(p => text.includes(p)) || timePattern.test(text)) {
                                status = text;
                            }
                            if (scorePattern.test(text.replace(/\\s/g, ''))) {
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
                                    if (!home) home = linkText;
                                    else if (!away && linkText !== home) away = linkText;
                                }
                            }
                        }

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
                    '.event-list', '.animation', '#animation', '[id*="live"]',
                    '.corner_tips', 'img.corner_tips'
                ];
                for (const sel of selectors) {
                    if (document.querySelector(sel)) return true;
                }
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

                const scoreSelectors = ['.score', '[class*="score"]', '.match-score', '.live-score'];
                for (const sel of scoreSelectors) {
                    const elem = document.querySelector(sel);
                    if (elem) {
                        const text = elem.innerText.trim();
                        if (/^\\d+\\s*[:：]\\s*\\d+$/.test(text.replace(/\\s/g, ''))) {
                            score = text;
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
        """使用DOM方式精确提取角球事件 - 增强版（支持img.corner_tips）"""
        try:
            events = await page.evaluate('''() => {
                const cornerEvents = [];
                const seen = new Set();

                // 🔴 策略1：优先提取 img.corner_tips 的 title 属性
                const cornerImgs = document.querySelectorAll('img.corner_tips, img[class*="corner"]');
                for (const img of cornerImgs) {
                    const title = img.getAttribute('title');
                    if (title && title.includes('角球')) {
                        const normalized = title.trim();
                        if (normalized.length < 200 && !seen.has(normalized)) {
                            seen.add(normalized);
                            cornerEvents.push(normalized);
                        }
                    }
                }

                // 策略2：从事件容器中提取
                const containerSelectors = [
                    '.event-list', '.timeline', '[class*="event"]', '[class*="live-animation"]',
                    '#animation', '.match-events', '.live-text', 'div[class*="text"]',
                    '.tips_panel', 'div[class*="tips"]'
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

                    if (text.includes('角球') && (text.includes('获得') || text.includes('角球'))) {
                        let fullEvent = text;
                        if (currentTime) {
                            fullEvent = currentTime + ' ' + text;
                            currentTime = '';
                        } else if (/^\\d+['′′′]/.test(text.substring(0, 6))) {
                            fullEvent = text;
                        }

                        const normalized = fullEvent.trim();
                        if (normalized.length < 200 && !seen.has(normalized)) {
                            seen.add(normalized);
                            cornerEvents.push(normalized);
                        }
                    }

                    if (text.length > 100) {
                        currentTime = '';
                    }
                }

                // 策略3：查找包含"角球"的所有元素
                const cornerElems = container.querySelectorAll('*');
                for (const elem of cornerElems) {
                    const text = elem.innerText.trim();
                    if (text.includes('角球') && text.includes('获得') && text.length < 200) {
                        let full = text;
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

                // 🔴 策略4：查找所有带 title 属性且包含"角球"的元素
                const allWithTitle = document.querySelectorAll('[title]');
                for (const elem of allWithTitle) {
                    const title = elem.getAttribute('title');
                    if (title && title.includes('角球')) {
                        const normalized = title.trim();
                        if (normalized.length < 200 && !seen.has(normalized)) {
                            seen.add(normalized);
                            cornerEvents.push(normalized);
                        }
                    }
                }

                return cornerEvents;
            }''')
            
            if events:
                print(f"  提取到 {len(events)} 个角球事件")
            return events
        except Exception as e:
            print(f"DOM提取角球事件出错: {e}")
            return []


async def extract_all_events_dom(self, page: Page) -> List[str]:
        """使用DOM方式提取所有事件"""
        try:
            events = await page.evaluate('''() => {
                const allEvents = [];
                const seen = new Set();

                // 🔴 新增：提取所有带 title 的图片元素
                const allImgs = document.querySelectorAll('img[title]');
                for (const img of allImgs) {
                    const title = img.getAttribute('title');
                    if (title && title.length > 3 && title.length < 200) {
                        const normalized = title.trim();
                        if (!seen.has(normalized)) {
                            seen.add(normalized);
                            allEvents.push(normalized);
                        }
                    }
                }

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

                    if (text.length > 3 && text.length < 200 &&
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
        """保存角球专用数据到JSON"""
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
                home_corners = len([c for c in corners if '主队' in c or 'home' in c.lower() or '主' in c])
                away_corners = len([c for c in corners if '客队' in c or 'away' in c.lower() or '客' in c])

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
            print(f"✓ 角球数据已保存到 {self.corner_file} (共 {total_corners} 个角球)")

        except Exception as e:
            print(f"保存角球数据失败: {str(e)}")

    def print_live_table(self):
        """打印实时监控表格"""
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\n" + "="*130)
        print("足球角球实时监控系统 (DOM解析版 - 无头模式 - 增强版)".center(130))
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

        if total_corners > 0:
            print("\n⚽ 近期角球事件详情:")
            print("="*130)
            for match_id, data in sorted(self.corner_only_data.items()):
                corners = data.get('corners', [])
                if corners:
                    info = data['match_info']
                    print(f"\n🏆 {info['home']} vs {info['away']} ({info['score']}) - 共 {len(corners)} 个角球")
                    for i, event in enumerate(corners[-15:], 1):  # 显示最近15个
                        print(f"  {i:>2}. {event}")


async def monitor_single_match(self, match_info: Dict):
        """监控单场比赛 - 增强版"""
        match_id = match_info['id']
        page = None

        try:
            page = await self.context.new_page()
            self.monitoring_pages[match_id] = page

            print(f"[{match_id}] 启动监控: {match_info['home']} vs {match_info['away']}")

            await page.goto(match_info['url'], wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)  # 🔴 增加等待时间，确保页面完全加载

            # 尝试点击进入动画直播
            clicked = False
            for text in ['动画直播', '直播数据', '动画', '技术统计', '文字直播']:
                try:
                    await page.click(f'text={text}', timeout=5000)
                    await asyncio.sleep(3)
                    clicked = True
                    print(f"[{match_id}] 已进入 {text}")
                    break
                except:
                    continue

            # 🔴 额外等待，确保动画元素加载
            await asyncio.sleep(3)

            # 更新队伍信息
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
            no_corner_count = 0  # 🔴 新增：连续无角球计数

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

                    # 🔴 提取事件（优先角球）
                    corner_events = await self.extract_corner_events_dom(page)
                    all_events = await self.extract_all_events_dom(page)

                    # 更新角球事件
                    existing_corners = self.corner_only_data[match_id]['corners']
                    new_corners = [c for c in corner_events if c not in existing_corners]
                    existing_corners.extend(new_corners)

                    # 更新所有事件
                    existing_all = self.corner_data[match_id]['events']
                    new_all = [e for e in all_events if e not in existing_all]
                    existing_all.extend(new_all)

                    # 🔴 有新角球时立即保存并打印
                    if new_corners:
                        self.save_corner_data()
                        print(f"[{match_id}] 🎯 新增 {len(new_corners)} 个角球:")
                        for c in new_corners:
                            print(f"    ⚽ {c}")
                        no_corner_count = 0
                    else:
                        no_corner_count += 1

                    # 定期刷新表格
                    now = asyncio.get_event_loop().time()
                    if new_all or new_corners or (now - last_update > 10):
                        self.print_live_table()
                        last_update = now

                    # 🔴 如果长时间无角球且比赛可能已结束，检查状态
                    if no_corner_count > 20 and '完场' in self.corner_data[match_id]['match_info'].get('status', ''):
                        print(f"[{match_id}] 比赛已完场，关闭监控")
                        break

                    await asyncio.sleep(3)

                except Exception as e:
                    print(f"[{match_id}] 监控循环异常: {e}")
                    await asyncio.sleep(5)

        except Exception as e:
            print(f"[{match_id}] 启动失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if page and not page.is_closed():
                try:
                    await page.close()
                except:
                    pass
            if match_id in self.monitoring_pages:
                del self.monitoring_pages[match_id]


async def run(self):
    """主运行函数"""
    await self.init_browser(headless=True)
    
    try:
        while True:
            matches = await self.get_live_matches()
            
            if not matches:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 暂无进行中的比赛，等待 {self.refresh_interval}s 后重新扫描...")
                await asyncio.sleep(self.refresh_interval)
                continue
            
            # 启动新比赛的监控
            tasks = []
            for match in matches:
                if match['id'] not in self.monitoring_pages:
                    task = asyncio.create_task(self.monitor_single_match(match))
                    tasks.append(task)
            
            if tasks:
                print(f"\n启动 {len(tasks)} 场新比赛的监控...")
                await asyncio.sleep(5)
            
            # 等待后重新扫描
            await asyncio.sleep(self.refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n检测到中断信号，正在保存数据并关闭...")
        self.save_corner_data()
    except Exception as e:
        print(f"\n主循环异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await self.close_browser()
        print("✓ 浏览器已关闭，程序退出")


async def main():
    """程序入口"""
    scraper = CornerKickScraper()
    try:
        await scraper.run()
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper.browser:
            await scraper.close_browser()


if __name__ == "__main__":
    print("="*80)
    print("足球角球实时监控系统 (DOM解析版 - 无头模式 - 增强版)".center(80))
    print("="*80)
    print("\n功能特点:")
    print("  ✓ 无头浏览器运行")
    print("  ✓ 自动扫描进行中的比赛")
    print("  ✓ DOM方式精确提取角球事件（支持 img.corner_tips）")
    print("  ✓ 实时监控并保存到 corner_only_data.json")
    print("  ✓ 智能关闭无效比赛（0:0超时、无事件区域）")
    print("  ✓ 支持中断保存（Ctrl+C）")
    print("\n正在启动...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已安全退出")
