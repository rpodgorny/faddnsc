use clap::Parser;
use ini::Ini;

#[derive(Debug, Parser)]
#[command(version = env!("CARGO_PKG_VERSION"))]
pub struct Args {
    /// path to config file
    #[arg(short = 'c', long)]
    pub config: Option<String>,
    /// base url to send data to
    #[arg(short, long)]
    pub url: Option<String>,
    /// hostname to be identified as
    #[arg(long)]
    pub host: Option<String>,
    /// update interval in seconds
    #[arg(short, long)]
    pub interval: Option<u64>,
}

impl Args {
    // TODO: for some reason, i can't use ::parse() directly outside this module
    pub fn parse_() -> Self {
        Self::parse()
    }
}

#[derive(Debug, Default)]
pub struct IniConfig {
    url: Option<String>,
    host: Option<String>,
    interval: Option<u64>,
}

impl IniConfig {
    pub fn from_file(fn_: &str) -> Self {
        Ini::load_from_file(fn_).map_or(Self::default(), |ini_| Self {
            url: ini_.get_from(Some("General"), "Url").map(|x| x.to_owned()),
            host: ini_.get_from(Some("General"), "Host").map(|x| x.to_owned()),
            interval: ini_
                .get_from(Some("General"), "Interval")
                .and_then(|x| x.parse().ok()),
        })
    }
}

#[derive(Debug)]
pub struct Config {
    pub url: String,
    pub host: String,
    pub interval: u64,
}

impl Config {
    // TODO: if we consumed args, we wouldn't have to do all the cloning
    pub fn from_ini_and_args(ini: IniConfig, args: &Args) -> anyhow::Result<Self> {
        let url = args
            .url
            .clone()
            .or(ini.url)
            .ok_or_else(|| anyhow::anyhow!("no url configured"))?;
        let host = if let Some(host) = args.host.clone() {
            host
        } else if let Some(host) = ini.host {
            host
        } else {
            hostname::get().unwrap().to_str().unwrap().to_string()
        };
        let interval = args.interval.or(ini.interval).unwrap_or(600);
        Ok(Self {
            url,
            host,
            interval,
        })
    }
}
