CREATE TABLE stocks (
    stock_code varchar,
    stock_name varchar,
    avg_volume int,
    comments_count int,
    recent_comments_json varchar,
    price float
);


CREATE TABLE stock_log (
    stock_code varchar,
    timestamp timestamp,
    last_comment varchar,
    volume int,
    price float,
    is_penny boolean
);