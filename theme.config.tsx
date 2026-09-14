import React from 'react'
import { DocsThemeConfig } from 'nextra-theme-docs'

const config: DocsThemeConfig = {
  useNextSeoProps() {
    return {
      titleTemplate: '%s – Beplus Site Assistant'
    }
  },
  logo: (
    <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>
      Beplus Site Assistant Docs
    </span>
  ),
  project: {
    link: 'https://github.com/ducdung196qtr/beplus-site-assistant'
  },
  // The repository's default branch is master, not main. Pointing this at main
  // made every "edit this page" link 404, which is the one link a reader clicks
  // when something in the docs is wrong.
  docsRepositoryBase: 'https://github.com/ducdung196qtr/beplus-site-assistant-doc/tree/master',
  footer: {
    text: `Beplus Site Assistant - AI Website Assistant for WordPress © ${new Date().getFullYear()}`,
  },
}

export default config
