mod cfg;

use std::time::Duration;

const SLEEP: Duration = Duration::from_secs(600);  // TODO: hard-coded shit

fn log_init(fn_: Option<&str>) -> anyhow::Result<()> {
    let log_level_term = std::env::var("RUST_LOG").unwrap_or_else(|_| "info".to_owned());
    let log_level_term = match log_level_term.as_str() {
        "trace" => simplelog::LevelFilter::Trace,
        "info" => simplelog::LevelFilter::Info,
        "warn" => simplelog::LevelFilter::Warn,
        "error" => simplelog::LevelFilter::Error,
        _ => simplelog::LevelFilter::Debug,
    };
    let log_level_file = simplelog::LevelFilter::Debug;
    let log_config = simplelog::ConfigBuilder::new()
        .set_time_format_custom(time::macros::format_description!(
            "[year]-[month]-[day] [hour]:[minute]:[second].[subsecond digits:6]"
        ))
        .set_time_offset_to_local()
        .expect("setting time offset to local should never fail")
        .build();
    let termlogger = simplelog::TermLogger::new(
        log_level_term,
        log_config.clone(),
        simplelog::TerminalMode::Stderr,
        simplelog::ColorChoice::Auto,
    );
    if let Some(fn_) = fn_ {
        simplelog::CombinedLogger::init(vec![
            termlogger,
            simplelog::WriteLogger::new(
                log_level_file,
                log_config,
                std::fs::OpenOptions::new()
                    .append(true)
                    .create(true)
                    .open(fn_)?,
            ),
        ])?;
    } else {
        simplelog::CombinedLogger::init(vec![termlogger])?;
    }

    log_panics::init();

    Ok(())
}

fn main() -> anyhow::Result<()> {
    let args = cfg::Args::parse_();

    #[cfg(target_os = "windows")]
    let log_fn = Some("/faddnsc/faddnsc.log");
    #[cfg(target_os = "linux")]
    let log_fn = None;
    log_init(log_fn).expect("logging init should never fail");

    let version = env!("CARGO_PKG_VERSION");

    log::info!("******************************");
    log::info!("starting faddnsc v{version}");
    log::debug!("args: {args:?}");

    #[cfg(target_os = "windows")]
    let cfg_fn = "/faddnsc/faddnsc.ini";
    #[cfg(target_os = "linux")]
    let cfg_fn = "/etc/faddnsc.conf";
    log::debug!("cfg_fn: {cfg_fn:?}");
    let cfg_ini = cfg::IniConfig::from_file(cfg_fn);
    log::debug!("cfg_ini: {cfg_ini:?}");

    let cfg = cfg::Config::from_ini_and_args(cfg_ini, &args);
    log::debug!("cfg: {cfg:?}");

    loop {
        let ips = local_ip_address::list_afinet_netifas()?
            .into_iter()
            .map(|(_name, ip)| {
                (
                    if ip.is_ipv4() { "inet" } else { "inet6" },
                    ip.to_string(),
                )
            })
            .collect::<Vec<_>>();
        log::debug!("{ips:?}");

        let mut url = url::Url::parse(&cfg.url)?;
        url.query_pairs_mut()
            .append_pair("host", &cfg.host)
            .append_pair("version", version);
        for (family, ip) in ips {
            url.query_pairs_mut().append_pair(family, &ip);
        }
        let result = ureq::get(url.as_str()).call();
        log::debug!("DNS update response: {result:?}");
        if let Err(err) = &result {
            log::error!("Failed to update DNS: {err}");
        }

        std::thread::sleep(SLEEP);

        // TODO: to get rid of unreachable code below
        if false {
            break;
        }
    }

    Ok(())
}
