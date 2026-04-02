/*
 * ngx_http_replace_cbor_module.c
 * Copyright (C) 2026 TU Dresden
 *
 * Distributed under terms of the MIT license.
 */

#include <ngx_config.h>
#include <ngx_core.h>
#include <ngx_http.h>

#include <Python.h>

static ngx_int_t ngx_http_replace_cbor_handler(ngx_http_request_t *r);
static char *ngx_http_replace_cbor(ngx_conf_t *cf, ngx_command_t *cmd, void *conf);
static ngx_int_t init_master(ngx_log_t *log);
static void exit_master(ngx_cycle_t *cycle);


static ngx_command_t ngx_http_replace_cbor_commands[] = {

    {
        ngx_string("replace_cbor"),                /* how we activate this module in config file */
        NGX_HTTP_LOC_CONF | NGX_CONF_NOARGS,       /* module accepts no values */
        ngx_http_replace_cbor,                     /* module configuration function */
        0,
        0,
        NULL
    },
    ngx_null_command /* end of commands */
};

static ngx_http_module_t ngx_http_replace_cbor_module_ctx = {
    NULL, /* preconfiguration */
    NULL, /* postconfiguration */

    NULL, /* create main configuration */
    NULL, /* init main configuration */

    NULL, /* create server configuration */
    NULL, /* merge server configuration */

    NULL, /* create location configuration */
    NULL  /* merge location configuration */
};

ngx_module_t ngx_http_replace_cbor_module = {
    NGX_MODULE_V1,
    /* module context */
    &ngx_http_replace_cbor_module_ctx,  /* void *ctx  */
    /* module directives */
    ngx_http_replace_cbor_commands,     /* ngx_command_t *command */
    /* module type */
    NGX_HTTP_MODULE,                    /* type */
    /* init master */
    init_master,                        /* (*init_master)(ngx_log_t *log); */
    /* init module */
    NULL,                               /* (*init_module)(ngx_cycle_t *cycle); */
    /* init process */
    NULL,                               /*  (*init_process)(ngx_cycle_t *cycle); */
    /* init thread */
    NULL,                               /* (*init_thread)(ngx_cycle_t *cycle); */
    /* exit thread */
    NULL,                               /* (*exit_thread)(ngx_cycle_t *cycle); */
    /* exit process */
    NULL,                               /* (*exit_process)(ngx_cycle_t *cycle); */
    /* exit master */
    exit_master,                        /* (*exit_master)(ngx_cycle_t *cycle); */
    NGX_MODULE_V1_PADDING
};

static PyObject *json2cbor;

static void ngx_http_replace_cbor_cleanup_pyobj(void *data)
{
    PyObject *result = data;

    Py_XDECREF(result);
}

static ngx_int_t ngx_http_replace_cbor_handler(ngx_http_request_t *r)
{
    ngx_buf_t *b;
    ngx_chain_t out;
    ngx_str_t msg;
    ngx_pool_cleanup_t *cln;
    Py_ssize_t result_size;

    PyObject *args = PyTuple_Pack(1, PyBytes_FromString("{\"foobar\":1.2}"));
    PyObject *result = PyObject_CallObject(json2cbor, args);

    if (PyBytes_AsStringAndSize(result, (char **)&msg.data, &result_size) != 0 && 
        result_size < 0) {
        ngx_log_debug0(NGX_LOG_DEBUG_HTTP, r->connection->log, 0,
                       "Unable to fetch json2cbor return value");
        Py_XDECREF(args);
        Py_XDECREF(result);
        return NGX_ERROR;
    }

    Py_XDECREF(args);

    msg.len = (size_t)result_size;

    ngx_log_debug0(NGX_LOG_DEBUG_HTTP, r->connection->log, 0, "http echo handler!");

    /* set response buffer for writing response  */
    b = ngx_pcalloc(r->pool, sizeof(ngx_buf_t));

    cln = ngx_pool_cleanup_add(r->pool, 0);
    if (cln == NULL) {
        return NGX_ERROR;
    }

    cln->data = result;
    cln->handler = ngx_http_replace_cbor_cleanup_pyobj;

    /* populate buffer chain. */
    out.buf = b;
    out.next = NULL; /* no more buffers */

    b->pos = msg.data;            
    b->last = msg.data + msg.len; 
    b->memory = 1;                
    b->last_buf = 1;              

    /* set output headers. */
    r->headers_out.status = NGX_HTTP_OK; 

    r->headers_out.content_length_n = msg.len;
    ngx_http_send_header(r); /* Send the headers */

    /* Send the body, and return the status code of the output filter chain. */
    return ngx_http_output_filter(r, &out);
}

static char *ngx_http_replace_cbor(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
{
    ngx_http_core_loc_conf_t *clcf = conf; /* pointer to core location configuration */

    clcf = ngx_http_conf_get_module_loc_conf(cf, ngx_http_core_module);
    clcf->handler = ngx_http_replace_cbor_handler;

    return NGX_CONF_OK;
}

static ngx_int_t init_master(ngx_log_t *log)
{
    PyObject *module_name, *module;

    Py_Initialize();

    module_name = PyUnicode_FromString("ngx_http_replace_cbor_module");
    module = PyImport_Import(module_name);
    json2cbor = PyObject_GetAttrString(module, (char *)"json2cbor");

    Py_XDECREF(module_name);
    Py_XDECREF(module);
    return 0;
}

static void exit_master(ngx_cycle_t *cycle)
{
    Py_XDECREF(json2cbor);
    Py_Finalize();
}
