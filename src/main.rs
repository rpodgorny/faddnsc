mod cfg;

use std::time::Duration;

fn ipv4_is_public(addr: &std::net::Ipv4Addr) -> bool {
    !(addr.is_private()
        || addr.is_loopback()
        || addr.is_link_local()
        || addr.is_unspecified()
        || addr.is_broadcast()
        || addr.is_documentation())
}

fn ipv6_is_public(addr: &std::net::Ipv6Addr) -> bool {
    let segs = addr.segments();
    let is_unique_local = (segs[0] & 0xfe00) == 0xfc00;
    let is_link_local = (segs[0] & 0xffc0) == 0xfe80;
    !(addr.is_loopback()
        || addr.is_unspecified()
        || addr.is_multicast()
        || is_unique_local
        || is_link_local)
}

fn log_init(fn_: Option<&str>) -> anyhow::Result<()> {
    let log_level = std::env::var("RUST_LOG").unwrap_or_else(|_| "info".to_owned());
    let log_level = match log_level.as_str() {
        "trace" => simplelog::LevelFilter::Trace,
        "debug" => simplelog::LevelFilter::Debug,
        "warn" => simplelog::LevelFilter::Warn,
        "error" => simplelog::LevelFilter::Error,
        _ => simplelog::LevelFilter::Info,
    };
    let log_level_term = log_level;
    let log_level_file = log_level;
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
    let system_cfg_fn = "/faddnsc/faddnsc.ini";
    #[cfg(target_os = "linux")]
    let system_cfg_fn = "/etc/faddnsc.conf";
    let cfg_fn: String = if let Some(c) = &args.config {
        if !std::path::Path::new(c).is_file() {
            anyhow::bail!("config file {c} does not exist");
        }
        c.clone()
    } else {
        let user_local = std::env::var_os("HOME")
            .or_else(|| std::env::var_os("USERPROFILE"))
            .map(|h| std::path::PathBuf::from(h).join(".faddnsc.conf"));
        match user_local {
            Some(p) if p.is_file() => p.to_string_lossy().into_owned(),
            _ => system_cfg_fn.to_string(),
        }
    };
    log::debug!("cfg_fn: {cfg_fn:?}");
    let cfg_ini = cfg::IniConfig::from_file(&cfg_fn);
    log::debug!("cfg_ini: {cfg_ini:?}");

    let cfg = cfg::Config::from_ini_and_args(cfg_ini, &args)?;
    log::debug!("cfg: {cfg:?}");

    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(60)))
        .build()
        .into();

    loop {
        let mut entries: Vec<(&'static str, String)> = Vec::new();
        for iface in netdev::get_interfaces() {
            if iface.is_loopback() {
                continue;
            }
            for ip in &iface.ipv4 {
                entries.push(("inet", ip.addr().to_string()));
            }
            for (i, ip) in iface.ipv6.iter().enumerate() {
                let flags = iface.ipv6_addr_flags.get(i).copied().unwrap_or_default();
                if flags.temporary || flags.deprecated || flags.tentative || flags.duplicated {
                    continue;
                }
                entries.push(("inet6", ip.addr().to_string()));
            }
            if let Some(mac) = iface.mac_addr {
                if mac != netdev::MacAddr::zero() {
                    entries.push(("ether", mac.address()));
                }
            }
        }
        log::debug!("{entries:?}");
        let has_ip_address = entries
            .iter()
            .any(|(family, _)| matches!(*family, "inet" | "inet6"));
        let has_public_ip_address = entries.iter().any(|(family, value)| match *family {
            "inet" => value
                .parse::<std::net::Ipv4Addr>()
                .is_ok_and(|a| ipv4_is_public(&a)),
            "inet6" => value
                .parse::<std::net::Ipv6Addr>()
                .is_ok_and(|a| ipv6_is_public(&a)),
            _ => false,
        });
        log::debug!(
            "has_ip_address={has_ip_address} has_public_ip_address={has_public_ip_address}"
        );
        log::info!("sending info to {} ({entries:?})", cfg.url);

        let mut url = url::Url::parse(&cfg.url)?;
        url.query_pairs_mut()
            .append_pair("host", &cfg.host)
            .append_pair("version", version);
        for (family, value) in entries {
            url.query_pairs_mut().append_pair(family, &value);
        }
        let result = agent.get(url.as_str()).call();
        log::debug!("DNS update response: {result:?}");
        if let Err(err) = &result {
            log::error!("Failed to update DNS: {err}");
        }

        let sleep = if !has_public_ip_address || result.is_err() {
            Duration::from_secs(60)
        } else {
            Duration::from_secs(cfg.interval)
        };
        std::thread::sleep(sleep);

        // TODO: to get rid of unreachable code below
        if false {
            break;
        }
    }

    Ok(())
}
