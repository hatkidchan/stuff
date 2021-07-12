const https = require('https')
/*
 * Author: [hatkidchan](https://github.com/hatkidchan)
 * 
 * Usage:
 * const getData = require('parse-awesome-selfhosted');
 * getData().then((result) => {
 *  for (const project of result) {
 *    // project.name, project.description, project.url, project.tags, etc
 *  }
 * });
 * 
 * Or:
 * const projects = await getData();
 * 
 */


const README_URL = 'https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md'
const REGEX_TAG = /`([^`]+)`/g
const REGEX_LINK = /\[([^\]]+)\]\(([^\)]+)\)/g
const REGEX_LINKS_LIST = /\((\[[^\]]+\]\([^\)]+\)[^\)]+)+\)/g
const REGEX_LINE_CONTENTS = /- \[([^\]]+)\]\(([^\)]+)\) - ([^`]+)/g

function http_get(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (req) => {
      let data = ''
      req.on('data', (chunk) => data += chunk)
      req.on('end', () => resolve(data))
      req.on('error', (err) => reject(error))
    })
  })
}

module.exports = async function () {
  const page = await http_get(README_URL)
  let currentCategory = null, shouldProcessLine = false, result = []
  for (const line of page.split('\n')) {
    if (line.startsWith('<!-- BEGIN SOFTWARE LIST -->')) {
      shouldProcessLine = true
    } else if (line.startsWith('<!-- END SOFTWARE LIST -->')) {
      shouldProcessLine = false
    } else if (shouldProcessLine && line.startsWith('### ')) {
      currentCategory = line.substr(4)
    } else if (shouldProcessLine && currentCategory !== null) {
      const line_match = REGEX_LINE_CONTENTS.exec(line)
      if (line_match) {
        let name = line_match[1]
        let url = line_match[2]
        let description = line_match[3]
        let tags_part = line.substr(line_match[0].length)

        let tags = []
        for (let match; match = REGEX_TAG.exec(tags_part); match) {
          tags.push(match[1])
        }
        
        let links = [], links_match
        if ((links_match = REGEX_LINKS_LIST.exec(description)) != null) {
          description = description.substr(0, links_match.index)
          for (let match; match = REGEX_LINK.exec(links_match[1]); match) {
            links.push({ name: match[1], url: match[2] })
          }
        }
        
        result.push({
          name, url, description, category: currentCategory, links, tags
        })
      }
    }
  }
  return result
}
