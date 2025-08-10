use clap::Parser;
use ini::Ini;

#[derive(Debug, Parser)]
#[command(version = env!("CARGO_PKG_VERSION"))]
pub struct Args {
    /// base url to send data to
    #[arg(short, long)]
    pub url: Option<String>,
    /// hostname to be identified as
    #[arg(long)]
    pub host: Option<String>,
}

impl Args {
    // TODO: for some reason, i can't use ::parse() directly outside this module
    pub fn parse_() -> Self {
        Self::parse()
    }
}

#[derive(Debug)]
pub struct IniConfig {
    url: Option<String>,
    host: Option<String>,
}

impl IniConfig {
    pub fn from_file(fn_: &str) -> Self {
        Ini::load_from_file(fn_).map_or(Self::default(), |ini_| Self {
            url: ini_.get_from(Some("General"), "Url").map(|x| x.to_owned()),
            host: ini_.get_from(Some("General"), "Host").map(|x| x.to_owned()),
        })
    }
}

impl Default for IniConfig {
    fn default() -> Self {
        Self {
            url: None,
            host: None,
        }
    }
}

#[derive(Debug)]
pub struct Config {
    pub url: String,
    pub host: String,
}

impl Config {
    // TODO: if we consumed args, we wouldn't have to do all the cloning
    pub fn from_ini_and_args(ini: IniConfig, args: &Args) -> Self {
        let url = if let Some(url) = args.url.clone() {
            url
        } else if let Some(url) = ini.url {
            url
        } else {
            "https://faddns.podgorny.cz".to_string()
        };
        let host = if let Some(host) = args.host.clone() {
            host
        } else if let Some(host) = ini.host {
            host
        } else {
            hostname::get().unwrap().to_str().unwrap().to_string()
        };
        Self { url, host }
    }
}
