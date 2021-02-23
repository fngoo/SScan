# -*- encoding: utf-8 -*-
# report template

import time
from string import Template
import webbrowser
import sys
import errno
import codecs
import os
from lib.common.utils import escape
from lib.common.consle_width import getTerminalSize
from config import setting
from config.log import logger
from config.banner import version
# template for html

html_general = """
<html>
<head>
<title>SScan ${version} Scan Report</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<style>
    body {width:960px; margin:auto; margin-top:10px; background:rgb(240,240,240);}
    p {color: #666;}
    h2 {color:#002E8C; font-size: 1em; padding-top:5px;}
    ul li {
    word-wrap: break-word;
    white-space: -moz-pre-wrap;
    white-space: pre-wrap;
    margin-bottom:10px;
    }
    span {color: purple;}
</style>
</head>
<body>
<p>Scanned <font color=red>${tasks_processed_count}</font> targets in 
<font color=green>${cost_min} ${cost_seconds} seconds</font>. 
<font color=red>${vulnerable_hosts_count}</font> vulnerable hosts found in total. </p>
${content}
</body>
</html>
"""

html_host = """
<h2>${host}</h2>
<ul>
${list}
</ul>
"""

html_list_item = """
 <li class="normal"> ${status} <span>${vul_type}</span> ${title}  <a href="${url}" target="_blank">${url}</a></li>
"""

html = {
    'general': html_general,
    'host': html_host,
    'list_item': html_list_item,
    'suffix': '.html'
}


# template for markdown
markdown_general = """
# BBScan Scan Report
Version: v 1.5
Num of targets: ${tasks_processed_count}
Num of vulnerable hosts: ${vulnerable_hosts_count}
Time cost: ${cost_min} ${cost_seconds} seconds
${content}
"""

markdown_host = """
## ${host}
${list}
"""

markdown_list_item = """* [${status}] ${title} ${url}
"""

markdown = {
    'general': markdown_general,
    'host': markdown_host,
    'list_item': markdown_list_item,
    'suffix': '.md'
}


# summary
template = {
    'html': html,
}


def save_report(args, _q_results, _file, tasks_processed_count):

    no_browser = args.browser
    start_time = time.time()
    a_template = template['html']
    t_general = Template(a_template['general'])
    t_host = Template(a_template['host'])
    t_list_item = Template(a_template['list_item'])
    output_file_suffix = a_template['suffix']
    report_name = '%s_%s%s' % (os.path.basename(_file).lower().replace('.txt', ''),
                               time.strftime('%Y%m%d_%H%M%S', time.localtime()),
                               output_file_suffix)

    html_doc = content = ""
    vulnerable_hosts_count = 0
    console_width = getTerminalSize()[0] - 2

    try:
        while not setting.stop_me or _q_results.qsize() > 0:
            if _q_results.qsize() == 0:
                time.sleep(0.1)
                continue

            while _q_results.qsize() > 0:
                item = _q_results.get()
                if type(item) is str:
                    message = '[%s] %s' % (time.strftime('%H:%M:%S', time.localtime()), item)
                    if args.network <= 22 and (item.startswith('Scan ') or item.startswith('No ports open')):
                        sys.stdout.write(message + (console_width - len(message)) * ' ' + '\r')
                    else:
                        logger.log('INFOR', f"{message}")
                    continue
                host, results = item
                vulnerable_hosts_count += 1

                # print
                for key in results.keys():
                    for url in results[key]:
                        logger.log('INFOR', f"[+]{url['status'] if url['status'] else ''} {url['url']}")

                _str = ""
                for key in results.keys():
                    for _ in results[key]:
                        _str += t_list_item.substitute(
                            {'status': ' [%s]' % _['status'] if _['status'] else '',
                             'url': _['url'],
                             'title': '[%s]' % _['title'] if _['title'] else '',
                             'vul_type': escape(_['vul_type'].replace('_', ' ')) if 'vul_type' in _ else ''}
                        )
                _str = t_host.substitute({'host': host, 'list': _str})
                content += _str

                cost_time = time.time() - start_time
                cost_min = int(cost_time / 60)
                cost_min = '%s min' % cost_min if cost_min > 0 else ''
                cost_seconds = '%.2f' % (cost_time % 60)

                html_doc = t_general.substitute({
                    'version': version,
                    'tasks_processed_count': tasks_processed_count,
                    'vulnerable_hosts_count': vulnerable_hosts_count,
                    'cost_min': cost_min, 'cost_seconds': cost_seconds, 'content': content
                })

                with codecs.open('report/%s' % report_name, 'w', encoding='utf-8') as outFile:
                    outFile.write(html_doc)

        # if config.ports_saved_to_file:
        #     print('* Ports data saved to %s' % args.save_ports)

        if html_doc:

            cost_time = time.time() - start_time
            cost_min = int(cost_time / 60)
            cost_min = '%s min' % cost_min if cost_min > 0 else ''
            cost_seconds = '%.1f' % (cost_time % 60)

            html_doc = t_general.substitute({
                'version': version,
                'tasks_processed_count': tasks_processed_count,
                'vulnerable_hosts_count': vulnerable_hosts_count,
                'cost_min': cost_min,
                'cost_seconds': cost_seconds,
                'content': content
            })

            with codecs.open('report/%s' % report_name, 'w', encoding='utf-8') as outFile:
                outFile.write(html_doc)

            time.sleep(1.0)

            logger.log('INFOR', '* %s vulnerable targets on sites in total.' % vulnerable_hosts_count)
            logger.log('INFOR', '* Scan report saved to report/%s' % report_name)
            #if no_browser:
            #    webbrowser.open_new_tab('file:///' + os.path.abspath('report/%s' % report_name))
        else:
            logger.log('INFOR', '* No vulnerabilities found on sites in %s.' % _file)

    except IOError as e:
        if e.errno == errno.EPIPE:
            sys.exit(-1)
    except Exception as e:
        logger.log('ERROR', '[save_report_thread Exception] %s %s' % (type(e), str(e)))
        import traceback
        traceback.print_exc()
        sys.exit(-1)
